import importlib

from fastapi.testclient import TestClient


SYSTEM_PROMPT = (
    "You are a careful assistant that answers only from the uploaded document. "
    "If the document does not contain the answer, say that you do not know from the provided context."
)

PROMPT_TEMPLATE = """Use only the information in the context below to answer the question.
If the answer is not in the context, say that you do not know from the provided context.

Context:
---
{context}
---

Question: {user_input}"""


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("EASY_ASSISTANT_DATA_FILE", str(tmp_path / "assistants.json"))
    monkeypatch.setenv("EASY_ASSISTANT_DEMO_MODE", "1")
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def create_jai_assistant(client: TestClient) -> str:
    response = client.post(
        "/api/assistants",
        json={
            "name": "JaiChat Study Assistant",
            "system_prompt": SYSTEM_PROMPT,
            "prompt_template": PROMPT_TEMPLATE,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def upload_jaichat_context(client: TestClient, assistant_id: str) -> None:
    context = (
        "JaiChat is a study chatbot built with FastAPI, vanilla HTML, CSS, and JavaScript.\n"
        "It demonstrates static RAG by pasting the full uploaded document into each model prompt."
    )
    response = client.post(
        f"/api/assistants/{assistant_id}/context",
        files={"file": ("jaichat.txt", context, "text/plain")},
    )
    assert response.status_code == 200


def test_static_rag_acceptance_flow(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    assistant_id = create_jai_assistant(client)
    upload_jaichat_context(client, assistant_id)

    answer_response = client.post(
        f"/api/assistants/{assistant_id}/chat",
        json={"user_input": "What is JaiChat built with?"},
    )
    assert answer_response.status_code == 200
    answer_payload = answer_response.json()
    assert "FastAPI" in answer_payload["reply"]
    assert "vanilla HTML" in answer_payload["reply"]
    assert "{context}" not in answer_payload["debug"]["filled_prompt"]
    assert "JaiChat is a study chatbot" in answer_payload["debug"]["filled_prompt"]
    assert answer_payload["debug"]["assistant_name"] == "JaiChat Study Assistant"
    assert answer_payload["debug"]["usage"]["prompt_tokens"] > 0

    unknown_response = client.post(
        f"/api/assistants/{assistant_id}/chat",
        json={"user_input": "Who won Roland Garros 2026?"},
    )
    assert unknown_response.status_code == 200
    unknown_payload = unknown_response.json()
    assert unknown_payload["reply"] == "I do not know from the provided context."
    assert unknown_payload["debug"]["usage"]["prompt_tokens"] > answer_payload["debug"]["usage"]["prompt_tokens"]


def test_model_messages_use_previous_bare_history_and_current_filled_prompt(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    assistant_id = create_jai_assistant(client)
    upload_jaichat_context(client, assistant_id)

    first = client.post(
        f"/api/assistants/{assistant_id}/chat",
        json={"user_input": "What is JaiChat built with?"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/assistants/{assistant_id}/chat",
        json={"user_input": "Who won Roland Garros 2026?"},
    )
    assert second.status_code == 200
    messages = second.json()["debug"]["messages_sent"]

    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1] == {"role": "user", "content": "What is JaiChat built with?"}
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"
    assert "Context:\n---\nJaiChat is a study chatbot" in messages[3]["content"]
    assert "Question: Who won Roland Garros 2026?" in messages[3]["content"]


def test_prompt_template_requires_static_rag_placeholders(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    response = client.post(
        "/api/assistants",
        json={
            "name": "Broken Assistant",
            "system_prompt": "Answer carefully.",
            "prompt_template": "Question: {user_input}",
        },
    )
    assert response.status_code == 400
    assert "{context}" in response.json()["detail"]


def test_saved_assistant_can_be_updated(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    assistant_id = create_jai_assistant(client)

    response = client.put(
        f"/api/assistants/{assistant_id}",
        json={
            "name": "Renamed Study Assistant",
            "system_prompt": SYSTEM_PROMPT,
            "prompt_template": PROMPT_TEMPLATE,
        },
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Study Assistant"
    assert response.json()["last_debug"]["assistant_name"] == "Renamed Study Assistant"
