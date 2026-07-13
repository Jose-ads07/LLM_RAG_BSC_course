# EASY-RAG

Week 2 Final Project for the BSC AI Factory course.

EASY-RAG extends the Week 2 EASY-ASSISTANT static RAG exercise into a dynamic RAG app:

- users create assistants;
- each assistant owns one persisted Chroma collection through the provided `collections-manager`;
- uploads are converted to markdown with MarkItDown;
- originals and markdown distillations are stored under `/static`;
- documents are chunked and inserted with provenance metadata;
- chat turns retrieve only the top-K chunks above the configured similarity threshold;
- answers show provenance and token usage.

## Run Locally

```bash
cd /Users/joseadsuara/Documents/Codex/week2/easy-rag
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
ollama serve
ollama pull qwen3:1.7b
ollama pull nomic-embed-text
.venv/bin/uvicorn app.main:app --reload
```

Open http://localhost:8001.

The app defaults to the local OpenAI-compatible Ollama endpoint:

```bash
export OPENAI_ENDPOINT="http://localhost:11434/v1"
export OPENAI_API_KEY="ollama"
export EASY_RAG_MODEL="qwen3:1.7b"
export EMBED_MODEL="nomic-embed-text"
```

For offline tests and demos without Ollama:

```bash
export EASY_ASSISTANT_DEMO_MODE=1
```

## Run Tests

```bash
cd /Users/joseadsuara/Documents/Codex/week2/easy-rag
.venv/bin/python -m pytest -q
```

## Docker

```bash
cd /Users/joseadsuara/Documents/Codex/week2/easy-rag
docker compose up --build
```

## Architecture

FastAPI serves the API and static frontend. Assistant definitions, visible chat history, document records, retrieval settings, and the latest debug payload are persisted in `data/assistants.json`.

Each assistant gets a stable collection name derived from its assistant id. Chroma persistence lives in `collections-store/`. The application talks only to the provided `collections-manager` functions: `create_collection`, `insert`, and `query`.

The browser UI is plain HTML/CSS/JS. It manages assistant settings, document upload, grounded chat, provenance display, and debug tabs for documents, retrieved chunks, filled prompt, messages, and usage.

## Ingestion Pipeline

1. The user uploads one or more documents.
2. The backend stores the original file in `static/uploads/{assistant_id}/`.
3. MarkItDown converts the original to markdown.
4. The markdown is stored in `static/markdown/{assistant_id}/`.
5. The selected chunking strategy creates chunks.
6. Each chunk is inserted into the assistant collection with metadata:
   `source`, `document_id`, `filename`, `doc_url`, `markdown_url`, `title`, `chunk_number`, `chunking_strategy`, and `ingested_at`.

## Retrieval Pipeline

1. The user message is the retrieval query.
2. The backend opens the assistant collection.
3. `query(collection, user_input, top_k, threshold)` returns the nearest chunks.
4. If no chunks pass the threshold, the app refuses with: `I do not know from the provided context.`
5. If chunks pass, they are formatted as markdown context with provenance and injected into the existing `{context}` / `{user_input}` prompt template.
6. The model receives the system prompt, previous bare history, and the current filled prompt.

## Chunking

Two configurable strategies are included from the Week 2 `simple-dynamic-rag` utility:

- `chars(size, overlap)`: sliding character windows. Default: size 800, overlap 100.
- `sections(level)`: markdown heading sections. Default heading level: 2.

The default is `chars` because it works on every converted document, including markdown without useful headings.

## Retrieval Settings

Default retrieval settings:

- `top_k = 4`
- `threshold = 0.4`

`top_k` controls how many nearest chunks can ride along in the prompt. The threshold gates weak matches before the model sees them.

## Provenance And Usage

Each assistant answer stores and displays:

- source document link;
- chunk number;
- similarity;
- token usage with `prompt_tokens`, `completion_tokens`, and `total_tokens` when available.

History keeps only bare `role` and `content` when building future model calls, so previous retrieved chunks are not re-sent accidentally.
