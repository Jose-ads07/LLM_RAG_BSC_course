# EASY-CHATGPT

EASY-CHATGPT is a small chatbot web application built with FastAPI, vanilla HTML/CSS/JavaScript, Ollama and an OpenAI-compatible API.

The project started as a baseline chatbot, but it now includes streaming responses, SQLite message storage, persistent conversations, a New chat system and previous chat selection.

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
- Docker support with `docker compose up --build`.
- Configuration through `.env`.

## Project structure

```text
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
