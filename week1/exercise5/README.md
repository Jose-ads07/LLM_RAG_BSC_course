EASY-CHATGPT — Week 1 Exercise 5

This is my Week 1 Exercise 5 project for the course Transformers, LLMs, RAG and Agents: From Theory to Production.

The goal of this exercise is to build a small but real chatbot server. The application has a FastAPI backend, a vanilla HTML/CSS/JavaScript frontend, a context view, and Docker support.

The project runs on port 6661.

What this project does

EASY-CHATGPT is a simple web chatbot.

The architecture is:

Browser
  → Frontend: HTML + CSS + JavaScript
  → Backend: FastAPI
  → LLM API: OpenAI-compatible endpoint / Ollama

The frontend does not call the model directly. Instead, the browser sends the user message to the FastAPI backend. The backend sends the conversation to the model and returns the answer to the frontend.

The page also shows a context view with:

* the model being used;
* the token usage returned by the API;
* the messages sent to the model.

Features implemented

* FastAPI REST backend.
* Vanilla JavaScript, HTML and CSS frontend.
* Chat window.
* Markdown rendering for model replies.
* Context view showing the messages sent to the model.
* Token usage display.
* Reset conversation button.
* Configuration through .env.
* Docker support with docker compose up.

This is the baseline version of the exercise. It does not implement streaming yet, so the model answer appears when the full response is ready.

Project structure

week1/exercise5/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md

Requirements

You need:

* Docker Desktop running;
* Ollama running on the host machine;
* the model qwen3:1.7b installed in Ollama.

You can check the installed Ollama models with:

ollama list

If the model is not installed, you can pull it with:

ollama pull qwen3:1.7b

Configuration

Copy the example environment file:

cp .env.example .env

For Docker, the .env file should contain:

OPENAI_BASE_URL=http://host.docker.internal:11434/v1
OPENAI_API_KEY=ollama
MODEL=qwen3:1.7b
PORT=6661

The value host.docker.internal is used because the backend runs inside Docker, but Ollama runs on the host machine.

The real .env file is not committed to GitHub.

How to run with Docker

From this folder:

cd week1/exercise5

start the application with:

docker compose up --build

Then open the browser at:

http://localhost:6661

To stop the application, press:

Ctrl + C

Then clean up the container with:

docker compose down

How to run locally without Docker

This was also useful during development.

From the week1/exercise5 folder:

python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 6661

For local execution without Docker, the .env file can use:

OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
MODEL=qwen3:1.7b
PORT=6661

Then open:

http://localhost:6661

Notes about the implementation

The backend keeps the conversation in memory using a Python list. Each user message and assistant answer is added to this list. This makes it possible to show the context view and to send the previous conversation turns back to the model.

The main backend route is:

POST /chat

It receives a user message, sends the full conversation to the model, receives the answer, stores it, and returns the answer plus token usage.

There is also a reset route:

POST /reset

This clears the conversation.

Current limitations

* No streaming yet. The frontend waits until the whole answer is ready.
* No persistent chat history. The conversation is kept only in memory.
* No user accounts.
* No vision support yet.

What I would improve next

The next improvement would be to add streaming with Server-Sent Events, so the answer appears token by token instead of arriving all at once.

After that, I would add persistent chat history using SQLite or JSON files.
