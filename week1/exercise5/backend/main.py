import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

from backend.database import (
    create_conversation,
    get_or_create_latest_conversation_id,
    init_database,
    list_conversations,
    load_messages,
    save_message,
)


load_dotenv()

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")
MODEL = os.getenv("MODEL", "qwen3:1.7b")

client = OpenAI(
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
)

app = FastAPI(title="EASY-CHATGPT")

init_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_conversation_id: int = get_or_create_latest_conversation_id()
conversation: List[Dict[str, str]] = load_messages(active_conversation_id)

last_usage: Dict[str, Any] = {
    "prompt_tokens": None,
    "completion_tokens": None,
    "total_tokens": None,
}


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return FileResponse("frontend/index.html")


@app.get("/state")
def state():
    """
    Returns the current backend state.
    The frontend uses this when the page loads.
    """
    return {
        "model": MODEL,
        "active_conversation_id": active_conversation_id,
        "conversations": list_conversations(),
        "messages_sent_to_model": conversation,
        "usage": last_usage,
    }


@app.post("/conversations/{conversation_id}/select")
def select_conversation(conversation_id: int):
    """
    Selects an existing conversation and loads its messages.
    """
    global active_conversation_id
    global conversation
    global last_usage

    active_conversation_id = conversation_id
    conversation = load_messages(active_conversation_id)

    last_usage = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }

    return {
        "status": "conversation selected",
        "model": MODEL,
        "active_conversation_id": active_conversation_id,
        "conversations": list_conversations(),
        "messages_sent_to_model": conversation,
        "usage": last_usage,
    }

@app.post("/chat")
def chat(request: ChatRequest) -> Dict[str, Any]:
    """
    Baseline non-streaming route.
    It is kept so the original version still exists.
    """
    user_message = request.message

    conversation.append({
        "role": "user",
        "content": user_message
    })
    save_message(active_conversation_id, "user", user_message)

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
    save_message(active_conversation_id, "assistant", assistant_message)

    usage = response.usage

    global last_usage
    last_usage = {
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
    }

    return {
        "answer": assistant_message,
        "messages_sent_to_model": conversation,
        "usage": last_usage,
        "model": MODEL,
        "active_conversation_id": active_conversation_id,
        "conversations": list_conversations(),
        "mode": "baseline",
    }


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    """
    Streaming route.
    It sends small chunks of the answer as they arrive from the model.
    The frontend reads these chunks and updates the assistant message live.
    """
    user_message = request.message

    conversation.append({
        "role": "user",
        "content": user_message
    })
    save_message(active_conversation_id, "user", user_message)

    def event_generator():
        assistant_parts: List[str] = []

        try:
            stream = client.chat.completions.create(
                model=MODEL,
                messages=conversation,
                temperature=0.7,
                stream=True,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta
                token = delta.content if delta and delta.content else ""

                if token:
                    assistant_parts.append(token)

                    yield "event: token\n"
                    yield f"data: {json.dumps({'token': token})}\n\n"

            assistant_message = "".join(assistant_parts)

            conversation.append({
                "role": "assistant",
                "content": assistant_message
            })
            save_message(active_conversation_id, "assistant", assistant_message)

            final_payload = {
                "model": MODEL,
                "active_conversation_id": active_conversation_id,
                "conversations": list_conversations(),
                "messages_sent_to_model": conversation,
                "usage": {
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                    "note": "Token usage is not available in this streaming response."
                },
                "mode": "streaming",
            }

            yield "event: done\n"
            yield f"data: {json.dumps(final_payload)}\n\n"

        except Exception as error:
            yield "event: error\n"
            yield f"data: {json.dumps({'error': str(error)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/reset")
def reset():
    """
    Deprecated behaviour.

    For compatibility, this now creates a new chat instead of deleting all stored messages.
    """
    return new_conversation()


app.mount("/static", StaticFiles(directory="frontend"), name="static")
