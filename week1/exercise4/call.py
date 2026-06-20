# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""
Call an LLM through the OpenAI-compatible Chat Completions API.

Runs UNCHANGED against:
  - your local Ollama          (the default below — no key, no money, no internet)
  - OpenAI / OpenRouter / Groq (set OPENAI_ENDPOINT + OPENAI_API_KEY in .env)

The wire format is the same everywhere. Only the .env changes.
"""
import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # pull OPENAI_ENDPOINT / OPENAI_API_KEY / MODEL from a local .env

client = OpenAI(
    base_url=os.environ.get("OPENAI_ENDPOINT", "http://localhost:11434/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "ollama"),  # Ollama ignores the value
)
model = os.environ.get("MODEL", "ministral-3:8b")

resp = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a terse assistant."},
        {"role": "user",   "content": "Say hello in one sentence."},
    ],
    temperature=1.5,
)

print(resp.choices[0].message.content)
print("---")
print("usage        :", resp.usage)             # prompt / completion / total tokens
print("finish_reason:", resp.choices[0].finish_reason)
