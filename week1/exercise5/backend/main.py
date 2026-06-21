import os
from typing import List, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel


load_dotenv()

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")
MODEL = os.getenv("MODEL", "qwen3:1.7b")

client = OpenAI(
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
)

app = FastAPI(title="EASY-CHATGPT")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conversation: List[Dict[str, str]] = []


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return FileResponse("frontend/index.html")


@app.post("/chat")
def chat(request: ChatRequest) -> Dict[str, Any]:
    user_message = request.message

    conversation.append({
        "role": "user",
        "content": user_message
    })

    response = client.chat.completions.create(
        model=MODEL,
        messages=conversation,
        temperature=0.7,
    )

    assistant_message = response.choices[0].message.content

    conversation.append({
        "role": "assistant",
        "content": assistant_message
    })

    usage = response.usage

    return {
        "answer": assistant_message,
        "messages_sent_to_model": conversation,
        "usage": {
            "prompt_tokens": usage.prompt_tokens if usage else None,
            "completion_tokens": usage.completion_tokens if usage else None,
            "total_tokens": usage.total_tokens if usage else None,
        },
        "model": MODEL,
    }


@app.post("/reset")
def reset():
    conversation.clear()
    return {"status": "conversation cleared"}


app.mount("/static", StaticFiles(directory="frontend"), name="static")
