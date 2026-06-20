# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""
Week 1 · Exercise 2 — Qwen3-1.7B (aligned model, 1.7B, 2025).

Heavily post-trained with supervised fine-tuning and preference optimization.
Same architecture family as GPT-2 (decoder-only transformer, next-token
prediction) — the difference is the alignment stack from Lecture 2.

Setup:
    uv venv && source .venv/bin/activate && uv sync
    python simple_qwen3.py

CPU-only, ~3.4 GB download on first run, cached afterward.
"""
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_ID = "Qwen/Qwen3-1.7B"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
model.eval()

print("Qwen3 1.7B CLI (Ctrl+C to quit)")

while True:
    try:
        user = input("\n> ").strip()
        if not user:
            continue

        messages = [{"role": "user", "content": user}]
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        inputs = tokenizer(prompt, return_tensors="pt")

        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=200,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )

        print("\n" + tokenizer.decode(output[0], skip_special_tokens=True))

    except KeyboardInterrupt:
        print("\nBye.")
        break
