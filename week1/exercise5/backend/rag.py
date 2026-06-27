import os
from typing import Dict, List, Tuple


RAG_CONTEXT_PATH = os.getenv("RAG_CONTEXT_PATH", "rag_files/context.md")


def load_rag_context() -> str:
    """
    Loads the local RAG context file.

    If the file does not exist, the app continues working without RAG context.
    """
    if not os.path.exists(RAG_CONTEXT_PATH):
        return ""

    with open(RAG_CONTEXT_PATH, "r", encoding="utf-8") as file:
        return file.read()


def build_messages_with_rag(
    conversation: List[Dict[str, str]]
) -> Tuple[List[Dict[str, str]], str]:
    """
    Builds the messages sent to the model.

    If a RAG context file exists, it is added as a system message.
    The model itself is not trained or modified.
    """
    context = load_rag_context()

    if not context.strip():
        return conversation, ""

    system_message = {
        "role": "system",
        "content": (
            "You are Jai, a local AI assistant.\n"
            "Answer the user's question using only the context provided below.\n"
            "If the answer is not in the context, say that you do not know from the provided context.\n\n"
            "Context:\n"
            "----\n"
            f"{context}\n"
            "----"
        )
    }

    return [system_message] + conversation, context
