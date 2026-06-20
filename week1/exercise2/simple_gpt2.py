# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""
Week 1 · Exercise 2 — GPT-2 (base model, 124M, 2019).

Never instruction-tuned, never RLHF'd. Pure next-token prediction over its
2019 web crawl. The point of this script: feel what a base model is.

Setup:
    uv venv && source .venv/bin/activate && uv sync
    python simple_gpt2.py

CPU-only, ~500 MB download on first run, cached afterward.
"""
from transformers import pipeline

# Load GPT-2 on CPU (default)
generator = pipeline("text-generation", model="gpt2")

print("GPT-2 CLI (Ctrl+C to quit)")

while True:
    try:
        prompt = input("\n> ")
        if not prompt.strip():
            continue

        output = generator(
            prompt,
            max_new_tokens=50,
            do_sample=True,
            temperature=0.8,
        )

        print("\n" + output[0]["generated_text"])

    except KeyboardInterrupt:
        print("\nBye.")
        break
