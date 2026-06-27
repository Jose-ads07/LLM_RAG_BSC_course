JaiChat

JaiChat is a local AI chat application built with FastAPI, vanilla HTML/CSS/JavaScript, Ollama and an OpenAI-compatible API.

It started as a simple Week 1 chatbot exercise, but it has been extended step by step with streaming responses, SQLite conversation storage, new chats, previous chat selection and automatic conversation titles.

The goal of the project is not only to build a chatbot, but also to understand how the different parts of a small LLM application fit together.

Features

* FastAPI backend.
* Vanilla HTML, CSS and JavaScript frontend.
* OpenAI-compatible model API.
* Local Ollama support.
* Streaming assistant responses.
* Markdown rendering for model answers.
* Context view showing what is sent to the model.
* SQLite message storage.
* Persistent conversations.
* New chat button.
* Previous chat selection.
* Automatic conversation titles from the first user message.
* Docker support with docker compose up --build.
* Configuration through .env.

Project structure

week1/exercise5/
├── backend/
│   ├── main.py
│   ├── database.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/
│   └── easy_chatgpt.db
├── screenshots/
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md

The data/ folder stores the local SQLite database. The database file is ignored by Git because it contains local conversations.

Requirements

You need:

* Docker Desktop.
* Ollama running locally.
* A local model available in Ollama.

For example:

ollama pull qwen3:1.7b

You can use another OpenAI-compatible model, but then you must update the MODEL value in the .env file.

Configuration

Copy the example environment file:

cp .env.example .env

For Docker, the .env file should look like this:

OPENAI_BASE_URL=http://host.docker.internal:11434/v1
OPENAI_API_KEY=ollama
MODEL=qwen3:1.7b
PORT=6661
DATABASE_PATH=data/easy_chatgpt.db

The important detail is:

host.docker.internal

When the backend runs inside Docker, localhost means the container itself. Since Ollama is running on the host machine, the container must use host.docker.internal to reach Ollama.

If you run the backend locally without Docker, you can use:

OPENAI_BASE_URL=http://localhost:11434/v1

Running the project with Docker

From the exercise folder:

cd week1/exercise5
docker compose up --build

Then open:

http://localhost:6661

To stop the project:

Ctrl + C
docker compose down

Running locally without Docker

You can also run the backend directly with Python.

From the exercise folder:

cd week1/exercise5
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 6661

For local execution, make sure your .env uses:

OPENAI_BASE_URL=http://localhost:11434/v1

Then open:

http://localhost:6661

How it works

The browser does not call the model directly.

The flow is:

Browser → FastAPI backend → Ollama/OpenAI-compatible API → FastAPI backend → Browser

The backend receives the user message, adds it to the active conversation, sends the conversation to the model, streams the answer back to the frontend, and stores both user and assistant messages in SQLite.

Backend

The backend is implemented in:

backend/main.py

It provides the main API routes and connects the frontend with the model.

Main routes:

GET  /
GET  /state
POST /chat
POST /chat/stream
POST /conversations/new
POST /conversations/{conversation_id}/select
POST /reset

The /reset route is kept for compatibility, but it now behaves like New chat: it creates a new conversation instead of deleting the old ones.

Streaming responses

The frontend uses:

POST /chat/stream

The backend returns server-sent events:

event: token
data: {"token": "..."}

The frontend reads the stream and updates Jai’s message progressively.

This makes the app feel more responsive because the user sees the answer while the model is still generating it.

SQLite conversation storage

Messages are stored in SQLite through:

backend/database.py

The database has two main tables:

conversations
messages

Each message has a conversation_id, so different chats can be stored separately.

This allows JaiChat to support:

* new chats;
* persistent history;
* previous chat selection;
* conversation reload after restarting Docker.

The database is stored at:

data/easy_chatgpt.db

In Docker, this folder is mounted as a volume:

volumes:
  - ./data:/app/data

This means that conversations are kept even if the Docker container is stopped and started again.

New chat and previous chats

The New chat button creates a new conversation without deleting the old ones.

The right panel shows a Previous chats section. Clicking a previous chat loads its messages back into the chat panel.

Conversation titles are generated automatically from the first user message. For example, if the first message is:

what is a RAG??

the chat title becomes something like:

what is a RAG?? #3

This makes the history easier to understand than a list of generic New chat entries.

Context view

The right panel shows:

* previous chats;
* model name;
* token usage;
* messages sent to the model.

This is useful for understanding what the backend actually sends to the LLM.

In streaming mode, token usage may not be fully available, so the backend includes a note explaining that.

Frontend

The frontend is built with plain HTML, CSS and JavaScript:

frontend/index.html
frontend/style.css
frontend/app.js

It does not use React, Vue or any frontend framework.

The JavaScript handles:

* sending user messages;
* reading streaming responses;
* rendering Markdown;
* loading saved conversations;
* selecting previous chats;
* creating new chats;
* updating the context view.

Current limitations

This is still a simple educational project.

Current limitations:

* no document-based RAG yet;
* no vector database;
* no user authentication;
* no multi-user support;
* token usage is limited in streaming mode;
* old conversations can be selected but not deleted from the UI;
* chat titles are simple and based only on the first user message.

Possible next improvements

Possible next steps:

* simple single-file RAG;
* show retrieved context in the context panel;
* upload a document from the frontend;
* delete or rename previous chats;
* export conversations as Markdown or JSON;
* better token usage tracking;
* support for tools or external account integrations.

Development progress

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

The next planned step is to add a simple RAG mode using one local document as context.
