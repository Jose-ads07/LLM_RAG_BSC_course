import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - requirements install this in normal use
    OpenAI = None

try:
    from markitdown import MarkItDown
except ImportError:  # pragma: no cover - requirements install this in normal use
    MarkItDown = None


BASE_DIR = Path(__file__).resolve().parent.parent
VENDOR_MANAGER = BASE_DIR / "vendor" / "collections-manager"
if VENDOR_MANAGER.exists():
    sys.path.insert(0, str(VENDOR_MANAGER))

from collections_manager import create_collection, insert, query

from app.chunking import chunk_by_chars, chunk_by_sections


STATIC_DIR = Path(os.getenv("EASY_RAG_STATIC_DIR", BASE_DIR / "static"))
UPLOADS_DIR = STATIC_DIR / "uploads"
MARKDOWN_DIR = STATIC_DIR / "markdown"
DEFAULT_DATA_FILE = BASE_DIR / "data" / "assistants.json"
DEFAULT_COLLECTIONS_DIR = BASE_DIR / "collections-store"
UNKNOWN_RESPONSE = "I do not know from the provided context."
DEFAULT_TOP_K = 4
DEFAULT_THRESHOLD = 0.4
DEFAULT_CHUNK_STRATEGY = "chars"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_SECTION_LEVEL = 2


STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="EASY-RAG")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AssistantCreate(BaseModel):
    name: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    prompt_template: str = Field(min_length=1)
    retrieval_top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=20)
    retrieval_threshold: float = Field(default=DEFAULT_THRESHOLD, ge=-1.0, le=1.0)
    chunk_strategy: str = Field(default=DEFAULT_CHUNK_STRATEGY, pattern="^(chars|sections)$")
    chunk_size: int = Field(default=DEFAULT_CHUNK_SIZE, ge=100, le=8000)
    chunk_overlap: int = Field(default=DEFAULT_CHUNK_OVERLAP, ge=0, le=4000)
    section_level: int = Field(default=DEFAULT_SECTION_LEVEL, ge=1, le=6)


class AssistantUpdate(AssistantCreate):
    pass


class ChatRequest(BaseModel):
    user_input: str = Field(min_length=1)


class IngestedDocument(BaseModel):
    id: str
    filename: str
    title: str
    doc_url: str
    markdown_url: str
    chunk_count: int
    inserted_count: int
    chunking_strategy: str
    ingested_at: str
    errors: list[str] = Field(default_factory=list)


def get_data_file() -> Path:
    return Path(os.getenv("EASY_ASSISTANT_DATA_FILE", DEFAULT_DATA_FILE))


def get_collections_dir() -> Path:
    return Path(os.getenv("EASY_RAG_COLLECTIONS_DIR", DEFAULT_COLLECTIONS_DIR))


def load_assistants() -> list[dict[str, Any]]:
    data_file = get_data_file()
    if not data_file.exists():
        return []

    try:
        data = json.loads(data_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Assistant store is invalid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="Assistant store must contain a JSON list.")
    return data


def save_assistants(assistants: list[dict[str, Any]]) -> None:
    data_file = get_data_file()
    data_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = data_file.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(assistants, indent=2), encoding="utf-8")
    tmp_file.replace(data_file)


def normalize_assistant(assistant: dict[str, Any]) -> dict[str, Any]:
    assistant.setdefault("documents", [])
    assistant.setdefault("history", [])
    assistant.setdefault("last_debug", None)
    assistant.setdefault("retrieval_top_k", DEFAULT_TOP_K)
    assistant.setdefault("retrieval_threshold", DEFAULT_THRESHOLD)
    assistant.setdefault("chunk_strategy", DEFAULT_CHUNK_STRATEGY)
    assistant.setdefault("chunk_size", DEFAULT_CHUNK_SIZE)
    assistant.setdefault("chunk_overlap", DEFAULT_CHUNK_OVERLAP)
    assistant.setdefault("section_level", DEFAULT_SECTION_LEVEL)
    assistant.setdefault("collection_name", collection_name_for(assistant["id"]))
    return assistant


def public_assistant(assistant: dict[str, Any]) -> dict[str, Any]:
    normalize_assistant(assistant)
    return {
        "id": assistant["id"],
        "name": assistant["name"],
        "system_prompt": assistant["system_prompt"],
        "prompt_template": assistant["prompt_template"],
        "retrieval_top_k": assistant["retrieval_top_k"],
        "retrieval_threshold": assistant["retrieval_threshold"],
        "chunk_strategy": assistant["chunk_strategy"],
        "chunk_size": assistant["chunk_size"],
        "chunk_overlap": assistant["chunk_overlap"],
        "section_level": assistant["section_level"],
        "collection_name": assistant["collection_name"],
        "documents": assistant["documents"],
        "document_count": len(assistant["documents"]),
        "chunk_count": sum(document.get("inserted_count", 0) for document in assistant["documents"]),
        "history": assistant.get("history", []),
        "last_debug": assistant.get("last_debug"),
    }


def find_assistant(assistant_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    assistants = load_assistants()
    for assistant in assistants:
        if assistant.get("id") == assistant_id:
            normalize_assistant(assistant)
            return assistants, assistant
    raise HTTPException(status_code=404, detail="Assistant not found.")


def validate_prompt_template(prompt_template: str) -> None:
    missing = [token for token in ("{context}", "{user_input}") if token not in prompt_template]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Prompt template must include: {', '.join(missing)}.",
        )


def fill_prompt(template: str, context: str, user_input: str) -> str:
    return template.replace("{context}", context).replace("{user_input}", user_input)


def build_messages(assistant: dict[str, Any], filled_prompt: str) -> list[dict[str, str]]:
    previous_history = [
        {"role": item["role"], "content": item["content"]}
        for item in assistant.get("history", [])
        if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)
    ]
    return [
        {"role": "system", "content": assistant["system_prompt"]},
        *previous_history,
        {"role": "user", "content": filled_prompt},
    ]


def debug_payload(
    assistant: dict[str, Any],
    context: str = "",
    retrieved_chunks: list[dict[str, Any]] | None = None,
    filled_prompt: str = "",
    messages: list[dict[str, str]] | None = None,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalize_assistant(assistant)
    return {
        "assistant_name": assistant["name"],
        "collection_name": assistant["collection_name"],
        "documents": assistant["documents"],
        "context_text": context,
        "retrieved_chunks": retrieved_chunks or [],
        "retrieval": {
            "top_k": assistant["retrieval_top_k"],
            "threshold": assistant["retrieval_threshold"],
        },
        "filled_prompt": filled_prompt,
        "messages_sent": messages or [],
        "usage": usage or {},
    }


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def estimate_usage(messages: list[dict[str, str]], reply: str) -> dict[str, Any]:
    prompt_tokens = sum(estimate_tokens(message["content"]) + 4 for message in messages)
    completion_tokens = estimate_tokens(reply)
    return {
        "provider": "local-demo",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "note": "Estimated locally because provider token usage was not returned.",
    }


def refusal_usage(reply: str) -> dict[str, Any]:
    completion_tokens = estimate_tokens(reply)
    return {
        "provider": "retrieval-gate",
        "prompt_tokens": 0,
        "completion_tokens": completion_tokens,
        "total_tokens": completion_tokens,
        "note": "No chunks passed the similarity threshold, so no model prompt was sent.",
    }


def important_terms(question: str) -> list[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "built",
        "did",
        "does",
        "for",
        "from",
        "how",
        "is",
        "it",
        "of",
        "the",
        "to",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "won",
    }
    words = re.findall(r"[A-Za-z0-9]+", question.lower())
    return [word for word in words if len(word) > 2 and word not in stop_words]


def sentence_split(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def local_demo_reply(context: str, question: str) -> str:
    terms = important_terms(question)
    if not terms:
        return UNKNOWN_RESPONSE

    scored_sentences: list[tuple[int, str]] = []
    for sentence in sentence_split(context):
        if sentence.startswith("[") and "]" in sentence:
            continue
        sentence_lower = sentence.lower()
        score = sum(1 for term in terms if term in sentence_lower)
        if score:
            scored_sentences.append((score, sentence))

    if not scored_sentences:
        return UNKNOWN_RESPONSE

    scored_sentences.sort(key=lambda item: item[0], reverse=True)
    return scored_sentences[0][1]


def demo_mode_enabled() -> bool:
    return os.getenv("EASY_ASSISTANT_DEMO_MODE", "").lower() in {"1", "true", "yes"}


def openai_enabled() -> bool:
    return not demo_mode_enabled() and OpenAI is not None


def call_model(messages: list[dict[str, str]], context: str, user_input: str) -> tuple[str, dict[str, Any]]:
    if not openai_enabled():
        reply = local_demo_reply(context, user_input)
        return reply, estimate_usage(messages, reply)

    model = os.getenv("EASY_RAG_MODEL", os.getenv("EASY_ASSISTANT_MODEL", os.getenv("MODEL", "qwen3:1.7b")))
    client = OpenAI(
        base_url=os.getenv("OPENAI_ENDPOINT", "http://localhost:11434/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "ollama"),
    )
    response = client.chat.completions.create(model=model, messages=messages)
    reply = response.choices[0].message.content or ""
    if response.usage:
        usage = response.usage.model_dump() if hasattr(response.usage, "model_dump") else response.usage.dict()
    else:
        usage = estimate_usage(messages, reply)
    usage["provider"] = "openai-compatible"
    usage["model"] = model
    return reply, usage


def slugify(value: str, fallback: str = "document") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-")
    return slug or fallback


def collection_name_for(assistant_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", assistant_id)
    return f"assistant_{safe}"[:63].strip("_-") or "assistant_collection"


def token_vector(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    if not tokens:
        vector[0] = 1.0
        return vector

    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def demo_embedding_function(texts: list[str]) -> list[list[float]]:
    return [token_vector(text) for text in texts]


def embedding_function():
    if demo_mode_enabled() or os.getenv("EASY_RAG_FAKE_EMBEDDINGS", "").lower() in {"1", "true", "yes"}:
        return demo_embedding_function
    return None


def assistant_collection(assistant: dict[str, Any]):
    normalize_assistant(assistant)
    get_collections_dir().mkdir(parents=True, exist_ok=True)
    return create_collection(
        assistant["collection_name"],
        embedding_function=embedding_function(),
        description=f"EASY-RAG collection for {assistant['name']}",
        metric="cosine",
        persist_path=str(get_collections_dir()),
    )


def convert_to_markdown(path: Path, raw: bytes) -> tuple[str, str]:
    if MarkItDown is not None:
        try:
            result = MarkItDown().convert(str(path))
            markdown = result.text_content or ""
            title = (result.title or path.stem).strip()
            if markdown.strip():
                return markdown, title
        except Exception as exc:
            if path.suffix.lower() not in {".txt", ".md", ".markdown"}:
                raise HTTPException(status_code=400, detail=f"Could not convert {path.name} to markdown: {exc}") from exc

    if path.suffix.lower() not in {".txt", ".md", ".markdown"}:
        raise HTTPException(status_code=400, detail="MarkItDown is required to convert this file type.")

    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError:
        markdown = raw.decode("utf-8", errors="replace")
    return markdown, path.stem


def chunk_markdown(assistant: dict[str, Any], markdown: str) -> tuple[list[str], str]:
    strategy = assistant["chunk_strategy"]
    if strategy == "sections":
        chunks = chunk_by_sections(markdown, level=assistant["section_level"])
        label = f"sections(level={assistant['section_level']})"
    else:
        chunks = chunk_by_chars(markdown, size=assistant["chunk_size"], overlap=assistant["chunk_overlap"])
        label = f"chars(size={assistant['chunk_size']},overlap={assistant['chunk_overlap']})"
    return chunks, label


def provenance_from_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    provenance = []
    for hit in hits:
        meta = hit["metadata"]
        provenance.append(
            {
                "source": meta.get("source", ""),
                "title": meta.get("title", meta.get("filename", "Untitled")),
                "filename": meta.get("filename", ""),
                "doc_url": meta.get("doc_url", ""),
                "markdown_url": meta.get("markdown_url", meta.get("md_url", "")),
                "chunk_number": meta.get("chunk_number", 0),
                "similarity": hit.get("similarity"),
                "chunking_strategy": meta.get("chunking_strategy", ""),
                "ingested_at": meta.get("ingested_at", ""),
            }
        )
    return provenance


def format_context(hits: list[dict[str, Any]]) -> str:
    blocks = []
    for hit in hits:
        meta = hit["metadata"]
        similarity = hit.get("similarity", 0)
        blocks.append(
            f"[{meta.get('title', 'Untitled')} | source {meta.get('doc_url', '')} | "
            f"chunk {meta.get('chunk_number', 0)} | similarity {similarity:.3f}]\n"
            f"{hit['chunk']}"
        )
    return "\n\n".join(blocks)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/assistants")
def list_assistants() -> list[dict[str, Any]]:
    return [public_assistant(assistant) for assistant in load_assistants()]


@app.post("/api/assistants")
def create_assistant(payload: AssistantCreate) -> dict[str, Any]:
    validate_prompt_template(payload.prompt_template)
    assistants = load_assistants()
    assistant_id = str(uuid4())
    assistant = {
        "id": assistant_id,
        "name": payload.name.strip(),
        "system_prompt": payload.system_prompt.strip(),
        "prompt_template": payload.prompt_template,
        "retrieval_top_k": payload.retrieval_top_k,
        "retrieval_threshold": payload.retrieval_threshold,
        "chunk_strategy": payload.chunk_strategy,
        "chunk_size": payload.chunk_size,
        "chunk_overlap": payload.chunk_overlap,
        "section_level": payload.section_level,
        "collection_name": collection_name_for(assistant_id),
        "documents": [],
        "history": [],
        "last_debug": None,
    }
    assistants.append(assistant)
    save_assistants(assistants)
    return public_assistant(assistant)


@app.put("/api/assistants/{assistant_id}")
def update_assistant(assistant_id: str, payload: AssistantUpdate) -> dict[str, Any]:
    validate_prompt_template(payload.prompt_template)
    assistants, assistant = find_assistant(assistant_id)
    assistant["name"] = payload.name.strip()
    assistant["system_prompt"] = payload.system_prompt.strip()
    assistant["prompt_template"] = payload.prompt_template
    assistant["retrieval_top_k"] = payload.retrieval_top_k
    assistant["retrieval_threshold"] = payload.retrieval_threshold
    assistant["chunk_strategy"] = payload.chunk_strategy
    assistant["chunk_size"] = payload.chunk_size
    assistant["chunk_overlap"] = payload.chunk_overlap
    assistant["section_level"] = payload.section_level
    assistant["last_debug"] = debug_payload(assistant)
    save_assistants(assistants)
    return public_assistant(assistant)


@app.get("/api/assistants/{assistant_id}")
def get_assistant(assistant_id: str) -> dict[str, Any]:
    _, assistant = find_assistant(assistant_id)
    return public_assistant(assistant)


@app.post("/api/assistants/{assistant_id}/documents")
async def upload_documents(assistant_id: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one document.")
    assistants, assistant = find_assistant(assistant_id)

    col = assistant_collection(assistant)
    ingested_documents: list[dict[str, Any]] = []
    assistant_upload_dir = UPLOADS_DIR / assistant_id
    assistant_markdown_dir = MARKDOWN_DIR / assistant_id
    assistant_upload_dir.mkdir(parents=True, exist_ok=True)
    assistant_markdown_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Uploaded document must have a filename.")

        raw = await file.read()
        document_id = str(uuid4())
        safe_name = slugify(file.filename)
        original_name = f"{document_id}-{safe_name}"
        original_path = assistant_upload_dir / original_name
        original_path.write_bytes(raw)

        markdown, title = convert_to_markdown(original_path, raw)
        markdown_name = f"{document_id}-{slugify(Path(safe_name).stem)}.md"
        markdown_path = assistant_markdown_dir / markdown_name
        markdown_path.write_text(markdown, encoding="utf-8")

        chunks, strategy_label = chunk_markdown(assistant, markdown)
        if not chunks:
            raise HTTPException(status_code=400, detail=f"{file.filename} produced no markdown chunks.")

        doc_url = f"/static/uploads/{assistant_id}/{original_name}"
        markdown_url = f"/static/markdown/{assistant_id}/{markdown_name}"
        ingested_at = dt.datetime.now(dt.UTC).isoformat()
        errors = []
        inserted_count = 0

        for chunk_number, chunk in enumerate(chunks):
            result = insert(
                col,
                chunk,
                {
                    "source": document_id,
                    "document_id": document_id,
                    "filename": file.filename,
                    "doc_url": doc_url,
                    "markdown_url": markdown_url,
                    "md_url": markdown_url,
                    "title": title,
                    "chunk_number": chunk_number,
                    "chunking_strategy": strategy_label,
                    "ingested_at": ingested_at,
                },
            )
            if result["ok"]:
                inserted_count += 1
            else:
                errors.append(f"chunk {chunk_number}: {result['error']}")

        document_model = IngestedDocument(
            id=document_id,
            filename=file.filename,
            title=title,
            doc_url=doc_url,
            markdown_url=markdown_url,
            chunk_count=len(chunks),
            inserted_count=inserted_count,
            chunking_strategy=strategy_label,
            ingested_at=ingested_at,
            errors=errors,
        )
        document = document_model.model_dump() if hasattr(document_model, "model_dump") else document_model.dict()
        assistant["documents"].append(document)
        ingested_documents.append(document)

    assistant["history"] = []
    assistant["last_debug"] = debug_payload(assistant, context=f"Ingested {len(ingested_documents)} document(s).")
    save_assistants(assistants)
    return {
        "assistant": public_assistant(assistant),
        "documents": ingested_documents,
        "collection_count": col.count(),
    }


@app.post("/api/assistants/{assistant_id}/context")
async def upload_context(assistant_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    return await upload_documents(assistant_id, [file])


@app.post("/api/assistants/{assistant_id}/chat")
def chat(assistant_id: str, payload: ChatRequest) -> dict[str, Any]:
    assistants, assistant = find_assistant(assistant_id)
    if not assistant["documents"]:
        raise HTTPException(status_code=400, detail="Upload at least one document before chatting.")

    col = assistant_collection(assistant)
    hits = query(
        col,
        payload.user_input,
        top_k=assistant["retrieval_top_k"],
        threshold=assistant["retrieval_threshold"],
    )
    provenance = provenance_from_hits(hits)

    if not hits:
        reply = UNKNOWN_RESPONSE
        usage = refusal_usage(reply)
        assistant.setdefault("history", []).extend(
            [
                {"role": "user", "content": payload.user_input},
                {"role": "assistant", "content": reply, "provenance": [], "usage": usage},
            ]
        )
        assistant["last_debug"] = debug_payload(
            assistant,
            context="",
            retrieved_chunks=[],
            filled_prompt="",
            messages=[],
            usage=usage,
        )
        save_assistants(assistants)
        return {
            "assistant": public_assistant(assistant),
            "reply": reply,
            "provenance": [],
            "debug": assistant["last_debug"],
        }

    context = format_context(hits)
    filled_prompt = fill_prompt(assistant["prompt_template"], context, payload.user_input)
    messages = build_messages(assistant, filled_prompt)
    reply, usage = call_model(messages, context, payload.user_input)

    assistant.setdefault("history", []).extend(
        [
            {"role": "user", "content": payload.user_input},
            {"role": "assistant", "content": reply, "provenance": provenance, "usage": usage},
        ]
    )
    assistant["last_debug"] = debug_payload(assistant, context, provenance, filled_prompt, messages, usage)
    save_assistants(assistants)

    return {
        "assistant": public_assistant(assistant),
        "reply": reply,
        "provenance": provenance,
        "debug": assistant["last_debug"],
    }


@app.post("/api/assistants/{assistant_id}/clear")
def clear_chat(assistant_id: str) -> dict[str, Any]:
    assistants, assistant = find_assistant(assistant_id)
    assistant["history"] = []
    assistant["last_debug"] = debug_payload(assistant)
    save_assistants(assistants)
    return public_assistant(assistant)
