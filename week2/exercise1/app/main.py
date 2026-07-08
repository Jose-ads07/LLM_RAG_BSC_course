import json
import os
import re
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


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_DATA_FILE = BASE_DIR / "data" / "assistants.json"
UNKNOWN_RESPONSE = "I do not know from the provided context."


app = FastAPI(title="EASY-ASSISTANT Static RAG")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AssistantCreate(BaseModel):
    name: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    prompt_template: str = Field(min_length=1)


class AssistantUpdate(AssistantCreate):
    pass


class ChatRequest(BaseModel):
    user_input: str = Field(min_length=1)


def get_data_file() -> Path:
    return Path(os.getenv("EASY_ASSISTANT_DATA_FILE", DEFAULT_DATA_FILE))


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


def public_assistant(assistant: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": assistant["id"],
        "name": assistant["name"],
        "system_prompt": assistant["system_prompt"],
        "prompt_template": assistant["prompt_template"],
        "context_filename": assistant.get("context_filename"),
        "context_text": assistant.get("context_text", ""),
        "history": assistant.get("history", []),
        "last_debug": assistant.get("last_debug"),
    }


def find_assistant(assistant_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    assistants = load_assistants()
    for assistant in assistants:
        if assistant.get("id") == assistant_id:
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
    previous_history = assistant.get("history", [])
    return [
        {"role": "system", "content": assistant["system_prompt"]},
        *previous_history,
        {"role": "user", "content": filled_prompt},
    ]


def debug_payload(
    assistant: dict[str, Any],
    filled_prompt: str = "",
    messages: list[dict[str, str]] | None = None,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "assistant_name": assistant["name"],
        "context_text": assistant.get("context_text", ""),
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
        "note": "Estimated locally because OPENAI_API_KEY is not configured.",
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
        sentence_lower = sentence.lower()
        score = sum(1 for term in terms if term in sentence_lower)
        if score:
            scored_sentences.append((score, sentence))

    if not scored_sentences:
        return UNKNOWN_RESPONSE

    scored_sentences.sort(key=lambda item: item[0], reverse=True)
    return scored_sentences[0][1]


def openai_enabled() -> bool:
    forced_demo = os.getenv("EASY_ASSISTANT_DEMO_MODE", "").lower() in {"1", "true", "yes"}
    return bool(os.getenv("OPENAI_API_KEY")) and not forced_demo and OpenAI is not None


def call_model(messages: list[dict[str, str]], context: str, user_input: str) -> tuple[str, dict[str, Any]]:
    if not openai_enabled():
        reply = local_demo_reply(context, user_input)
        return reply, estimate_usage(messages, reply)

    model = os.getenv("EASY_ASSISTANT_MODEL", "gpt-4o-mini")
    client = OpenAI()
    response = client.chat.completions.create(model=model, messages=messages)
    reply = response.choices[0].message.content or ""
    usage = response.usage.model_dump() if response.usage else {}
    usage["provider"] = "openai"
    usage["model"] = model
    return reply, usage


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
    assistant = {
        "id": str(uuid4()),
        "name": payload.name.strip(),
        "system_prompt": payload.system_prompt.strip(),
        "prompt_template": payload.prompt_template,
        "context_filename": None,
        "context_text": "",
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
    assistant["last_debug"] = debug_payload(assistant)
    save_assistants(assistants)
    return public_assistant(assistant)


@app.get("/api/assistants/{assistant_id}")
def get_assistant(assistant_id: str) -> dict[str, Any]:
    _, assistant = find_assistant(assistant_id)
    return public_assistant(assistant)


@app.post("/api/assistants/{assistant_id}/context")
async def upload_context(assistant_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Upload one plain-text .txt file.")

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")

    assistants, assistant = find_assistant(assistant_id)
    assistant["context_filename"] = file.filename
    assistant["context_text"] = text
    assistant["history"] = []
    assistant["last_debug"] = debug_payload(assistant)
    save_assistants(assistants)
    return public_assistant(assistant)


@app.post("/api/assistants/{assistant_id}/chat")
def chat(assistant_id: str, payload: ChatRequest) -> dict[str, Any]:
    assistants, assistant = find_assistant(assistant_id)
    context = assistant.get("context_text", "")
    if not context:
        raise HTTPException(status_code=400, detail="Upload a .txt context document before chatting.")

    filled_prompt = fill_prompt(assistant["prompt_template"], context, payload.user_input)
    messages = build_messages(assistant, filled_prompt)
    reply, usage = call_model(messages, context, payload.user_input)

    assistant.setdefault("history", []).extend(
        [
            {"role": "user", "content": payload.user_input},
            {"role": "assistant", "content": reply},
        ]
    )
    assistant["last_debug"] = debug_payload(assistant, filled_prompt, messages, usage)
    save_assistants(assistants)

    return {
        "assistant": public_assistant(assistant),
        "reply": reply,
        "debug": assistant["last_debug"],
    }


@app.post("/api/assistants/{assistant_id}/clear")
def clear_chat(assistant_id: str) -> dict[str, Any]:
    assistants, assistant = find_assistant(assistant_id)
    assistant["history"] = []
    assistant["last_debug"] = debug_payload(assistant)
    save_assistants(assistants)
    return public_assistant(assistant)
