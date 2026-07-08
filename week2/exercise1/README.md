# EASY-ASSISTANT

Week 2 Exercise 1: a static RAG assistant built with FastAPI and vanilla HTML/CSS/JS.

The app demonstrates the lecture pattern directly:

- the uploaded `.txt` document is pasted into the prompt on every chat turn;
- the visible chat history stores only bare user and assistant messages;
- the backend rebuilds the augmented prompt every turn;
- `prompt_tokens` is large because the whole document is sent each time.

No embeddings, vector search, chunking, agents, or document conversion are implemented.

## Run locally

```bash
cd week2/exercise1
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

With `OPENAI_API_KEY` set, the backend calls OpenAI Chat Completions. Without a key, it uses a small local demo responder so the static-RAG prompt construction and debug panel still work in class.

```bash
export OPENAI_API_KEY="sk-..."
export EASY_ASSISTANT_MODEL="gpt-4o-mini"
```

## Run with Docker

```bash
cd week2/exercise1
docker compose up --build
```

Assistant definitions, uploaded context text, visible chat history, and the latest debug payload are saved in `data/assistants.json`.

## Acceptance Walkthrough

Create an assistant named `JaiChat Study Assistant`.

Use this system prompt:

```text
You are a careful assistant that answers only from the uploaded document. If the document does not contain the answer, say that you do not know from the provided context.
```

Use this prompt template:

```text
Use only the information in the context below to answer the question.
If the answer is not in the context, say that you do not know from the provided context.

Context:
---
{context}
---

Question: {user_input}
```

Upload a short `.txt` document such as:

```text
JaiChat is a study chatbot built with FastAPI, vanilla HTML, CSS, and JavaScript.
It demonstrates static RAG by pasting the full uploaded document into each model prompt.
```

Ask `What is JaiChat built with?` and it should answer from the document.

Ask `Who won Roland Garros 2026?` and it should say that it does not know from the provided context.

Use the debug tabs to inspect the uploaded document, the filled prompt actually sent to the model, the complete model message list, and token usage including `prompt_tokens`.

## Tests

```bash
cd week2/exercise1
pytest
```

## Future Improvement

MarkItDown could be added later to convert PDFs, DOCX files, or slides into plain text before upload.
