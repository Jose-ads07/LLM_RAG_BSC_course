# JaiChat

JaiChat is a local AI chat application built with FastAPI, vanilla HTML/CSS/JavaScript, Ollama and an OpenAI-compatible API.

It started as a simple Week 1 chatbot exercise, but it has been extended step by step with streaming responses, SQLite conversation storage, new chats, previous chat selection, automatic conversation titles and simple single-file RAG.

The goal of the project is not only to build a chatbot, but also to understand how the different parts of a small LLM application fit together.

## Features

- FastAPI backend.
- Vanilla HTML, CSS and JavaScript frontend.
- OpenAI-compatible model API.
- Local Ollama support.
- Streaming assistant responses.
- Markdown rendering for model answers.
- Context view showing what is sent to the model.
- SQLite message storage.
- Persistent conversations.
- New chat button.
- Previous chat selection.
- Automatic conversation titles from the first user message.
- Simple single-file RAG.
- Docker support with `docker compose up --build`.
- Configuration through `.env`.

## Project structure

```text
week1/exercise5/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── rag.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── rag_files/
│   └── context.md
├── data/
│   └── easy_chatgpt.db
├── screenshots/
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

The `data/` folder stores the local SQLite database. The database file is ignored by Git because it contains local conversations.

The `rag_files/` folder contains the local Markdown file used as RAG context.

## Requirements

You need:

- Docker Desktop.
- Ollama running locally.
- A local model available in Ollama.

For example:

```bash
ollama pull qwen3:1.7b
```

You can use another OpenAI-compatible model, but then you must update the `MODEL` value in the `.env` file.

## Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

For Docker, the `.env` file should look like this:

```env
OPENAI_BASE_URL=http://host.docker.internal:11434/v1
OPENAI_API_KEY=ollama
MODEL=qwen3:1.7b
PORT=6661
DATABASE_PATH=data/easy_chatgpt.db
RAG_CONTEXT_PATH=rag_files/context.md
```

The important detail is:

```text
host.docker.internal
```

When the backend runs inside Docker, `localhost` means the container itself. Since Ollama is running on the host machine, the container must use `host.docker.internal` to reach Ollama.

If you run the backend locally without Docker, you can use:

```env
OPENAI_BASE_URL=http://localhost:11434/v1
```

## Running the project with Docker

From the exercise folder:

```bash
cd week1/exercise5
docker compose up --build
```

Then open:

```text
http://localhost:6661
```

To stop the project:

```bash
Ctrl + C
docker compose down
```

## Running locally without Docker

You can also run the backend directly with Python.

From the exercise folder:

```bash
cd week1/exercise5
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 6661
```

For local execution, make sure your `.env` uses:

```env
OPENAI_BASE_URL=http://localhost:11434/v1
```

Then open:

```text
http://localhost:6661
```

## How it works

The browser does not call the model directly.

The basic flow is:

```text
Browser → FastAPI backend → Ollama/OpenAI-compatible API → FastAPI backend → Browser
```

The backend receives the user message, adds it to the active conversation, builds the model input, streams the answer back to the frontend, and stores both user and assistant messages in SQLite.

With RAG enabled, the backend also loads a local Markdown file and adds it to the model call as hidden context.

## Backend

The backend is implemented mainly in:

```text
backend/main.py
```

It provides the API routes and connects the frontend with the model.

Main routes:

```text
GET  /
GET  /state
POST /chat
POST /chat/stream
POST /conversations/new
POST /conversations/{conversation_id}/select
POST /reset
```

The `/reset` route is kept for compatibility, but it now behaves like `New chat`: it creates a new conversation instead of deleting the old ones.

## Streaming responses

The frontend uses:

```text
POST /chat/stream
```

The backend returns server-sent events:

```text
event: token
data: {"token": "..."}
```

The frontend reads the stream and updates Jai's message progressively.

This makes the app feel more responsive because the user sees the answer while the model is still generating it.

## SQLite conversation storage

Messages are stored in SQLite through:

```text
backend/database.py
```

The database has two main tables:

```text
conversations
messages
```

Each message has a `conversation_id`, so different chats can be stored separately.

This allows JaiChat to support:

- new chats;
- persistent history;
- previous chat selection;
- conversation reload after restarting Docker.

The database is stored at:

```text
data/easy_chatgpt.db
```

In Docker, this folder is mounted as a volume:

```yaml
volumes:
  - ./data:/app/data
```

This means that conversations are kept even if the Docker container is stopped and started again.

## New chat and previous chats

The `New chat` button creates a new conversation without deleting the old ones.

The right panel shows a `Previous chats` section. Clicking a previous chat loads its messages back into the chat panel.

Conversation titles are generated automatically from the first user message. For example, if the first message is:

```text
what is a RAG??
```

the chat title becomes something like:

```text
what is a RAG?? #3
```

This makes the history easier to understand than a list of generic `New chat` entries.

## Simple single-file RAG

JaiChat includes a simple RAG implementation in:

```text
backend/rag.py
```

The current RAG version uses one local Markdown file:

```text
rag_files/context.md
```

The backend reads that file and adds it to the model call as a system message.

The visible chat history and the real model input are different:

```text
Visible chat:
user message + assistant answer

Real model call:
system message with RAG context + conversation history
```

This is important because the user sees a normal chat, but the model receives extra context.

The RAG instruction tells Jai to answer only from the provided context. If the answer is not in the context, Jai should say that it does not know from the provided context.

Example:

```text
Question: What is JaiChat?
Answer: JaiChat is a local AI chat application built with FastAPI, vanilla HTML/CSS/JavaScript, Ollama and an OpenAI-compatible API.
```

If the question is outside the context:

```text
Question: Who won Roland Garros 2026?
Answer: I do not know from the provided context.
```

This demonstrates the main RAG idea: the model is not trained with the document. The document is retrieved and inserted into the prompt at inference time.

## Context view

The right panel shows:

- previous chats;
- model name;
- token usage;
- messages sent to the model.

After adding RAG, the context view becomes more useful because it shows the real messages sent to the model, including the hidden system message with the RAG context.

This helps understand the difference between:

```text
chat_history
```

and:

```text
messages_sent_to_model
```

In streaming mode, token usage may not be fully available, so the backend includes a note explaining that.

## Frontend

The frontend is built with plain HTML, CSS and JavaScript:

```text
frontend/index.html
frontend/style.css
frontend/app.js
```

It does not use React, Vue or any frontend framework.

The JavaScript handles:

- sending user messages;
- reading streaming responses;
- rendering Markdown;
- loading saved conversations;
- selecting previous chats;
- creating new chats;
- updating the context view.

## Docker notes

The Dockerfile copies the backend, frontend and RAG files into the container:

```dockerfile
COPY backend /app/backend
COPY frontend /app/frontend
COPY rag_files /app/rag_files
```

The `COPY rag_files /app/rag_files` line is important. Without it, the RAG context file is not available inside Docker, and the model will answer without the intended context.

## Current limitations

This is still a simple educational project.

Current limitations:

- RAG uses the whole file every time.
- There is no chunking.
- There is no vector database.
- There is no semantic search yet.
- No user authentication.
- No multi-user support.
- Token usage is limited in streaming mode.
- Old conversations can be selected but not deleted from the UI.
- Chat titles are simple and based only on the first user message.

## Possible next improvements

Possible next steps:

- show the retrieved RAG context in a separate context panel section;
- upload a document from the frontend;
- split documents into chunks;
- retrieve only relevant chunks;
- add embeddings and vector search;
- delete or rename previous chats;
- export conversations as Markdown or JSON;
- better token usage tracking;
- support for tools or external account integrations.

## Development progress

The project was built step by step:

1. Baseline FastAPI chatbot.
2. Docker support.
3. Improved visual interface.
4. Streaming responses.
5. SQLite message storage.
6. New chat support.
7. Previous chat selection.
8. Automatic conversation titles.
9. Rename interface to JaiChat.
10. Simple single-file RAG.

The next planned step is to improve the RAG system by showing the retrieved context more clearly and later retrieving only the most relevant parts of a document.
