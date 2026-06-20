#!/usr/bin/env python3
# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""
Week 1 · Exercise 1 — Hugging Face tokenizers, locally.

Reference script for the exercise. You RUN this; you do not edit code (you
may swap the two paragraphs in PARAGRAPH_EN / PARAGRAPH_MINE for your own
text — that is the only change you need). You may also change the two
tokenizer ids (TOKENIZER_A / TOKENIZER_B) to compare different families.

It does three things and prints them clearly:
  1. loads a tokenizer with AutoTokenizer.from_pretrained(...) and shows a
     token count (the "how many tokens is this?" basic);
  2. tokenises the same paragraph in English and in another language, and
     computes the multilingual penalty;
  3. compares TWO tokenizers (different model families) on four kinds of
     code-ish input, and prints a small table.

Setup:
    uv venv
    source .venv/bin/activate
    uv sync
    python ex_01_tokenise.py

Only tokenizers are downloaded (a few hundred KB each) — no model weights,
no GPU, no API key, no network beyond the first Hugging Face download.

Good "old vs newer" contrast pairs, all ungated:
  - "gpt2"               (2019, byte-level BPE)
  - "bert-base-uncased"  (2018, WordPiece)
  - "bert-base-multilingual-cased" (multilingual WordPiece)
"""
from __future__ import annotations

# ---- the two tokenizers to compare -----------------------------------------
TOKENIZER_A = "gpt2"                 # the "older" one
TOKENIZER_B = "bert-base-uncased"    # the "newer-ish" one (different family)

# ---- the two paragraphs (you may replace with your own) --------------------
PARAGRAPH_EN = (
    "A large language model reads text as tokens, not words. The number of "
    "tokens — not the number of words — is what you are billed for and what "
    "must fit in the context window."
)
# Same paragraph, in your language. The default is Spanish; replace it with
# YOUR language for the exercise.
PARAGRAPH_MINE = (
    "Un gran model de llenguatge llig el text com a tokens, no com a paraules. "
    "El nombre de tokens — no el de paraules — és el que es factura i el que "
    "ha de cabre dins de la finestra de context."
)

# ---- four code-ish inputs for the tokenizer comparison ---------------------
CODE_SAMPLES = {
    "python function": (
        "def add(a, b):\n"
        "    \"\"\"Return the sum.\"\"\"\n"
        "    return a + b\n"
    ),
    "JSON blob": (
        '{"model": "gpt-4", "messages": [{"role": "user", '
        '"content": "hello"}], "max_tokens": 256}'
    ),
    "regex-heavy line": r"re.compile(r'^\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*;?$')",
    "whitespace-heavy": "x = 1\n\n\n\t\t\treturn          x\n\n",
}


def _load(name):
    from transformers import AutoTokenizer
    print(f"  loading tokenizer: {name} …")
    return AutoTokenizer.from_pretrained(name)


def n_tokens(tok, text: str) -> int:
    """Token count, not counting special tokens — what you pay for."""
    return len(tok.encode(text, add_special_tokens=False))


def main() -> None:
    # Windows consoles default to cp1252 and choke on — · → ± in our output.
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=" * 70)
    print("Week 1 · Exercise 1 — tokenizers, locally")
    print("=" * 70)

    print("\n[1] Load a tokenizer and count tokens")
    tok_a = _load(TOKENIZER_A)
    demo = "The model never sees the letters in strawberry."
    print(f'  text : "{demo}"')
    print(f"  tokens with {TOKENIZER_A}: {n_tokens(tok_a, demo)}")

    print("\n[2] The multilingual penalty (same paragraph, two languages)")
    en = n_tokens(tok_a, PARAGRAPH_EN)
    mine = n_tokens(tok_a, PARAGRAPH_MINE)
    penalty = (mine - en) / en if en else 0.0
    print(f"  English          : {en} tokens")
    print(f"  your language    : {mine} tokens")
    print(f"  multilingual penalty = (mine - en) / en = {penalty:+.1%}")
    print("  → record this number in your report.")

    print("\n[3] Two tokenizers vs four kinds of code")
    tok_b = _load(TOKENIZER_B)
    width = max(len(k) for k in CODE_SAMPLES) + 2
    print(f"\n  {'input':<{width}}{TOKENIZER_A:>14}{TOKENIZER_B:>20}")
    print("  " + "-" * (width + 34))
    for label, sample in CODE_SAMPLES.items():
        a, b = n_tokens(tok_a, sample), n_tokens(tok_b, sample)
        print(f"  {label:<{width}}{a:>14}{b:>20}")
    print("\n  → for each row, write ONE sentence: where do the two disagree")
    print("    most, and why might that be? (put it in your report)")

    print("\n" + "=" * 70)
    print("Done. Now write the report and push it to your course repo.")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except ModuleNotFoundError:
        raise SystemExit(
            "transformers is not installed. Run:\n"
            "    uv venv && source .venv/bin/activate && uv sync"
        )
