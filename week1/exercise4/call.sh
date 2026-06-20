#!/usr/bin/env bash
# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

# The same Chat Completions call, raw HTTP — no SDK, just curl.
# Defaults to your local Ollama. Override with env vars to hit a cloud provider.
[ -f .env ] && { set -a; . ./.env; set +a; }   # load .env if present (bash has no auto-load)
ENDPOINT="${OPENAI_ENDPOINT:-http://localhost:11434/v1}"
API_KEY="${OPENAI_API_KEY:-ollama}"
MODEL="${MODEL:-ministral-3:8b}"

curl "$ENDPOINT/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$MODEL"'",
    "messages": [
      {"role": "system", "content": "You are a terse assistant."},
      {"role": "user",   "content": "Say hello in one sentence."}
    ],
    "temperature": 0.7
  }'
