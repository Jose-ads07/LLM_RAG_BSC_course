import importlib

from fastapi.testclient import TestClient


SYSTEM_PROMPT = (
    "You are a careful assistant that answers only from the uploaded documents. "
    "If the documents do not contain the answer, say that you do not know from the provided context."
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
    monkeypatch.setenv("EASY_RAG_COLLECTIONS_DIR", str(tmp_path / "collections-store"))
    monkeypatch.setenv("EASY_RAG_STATIC_DIR", str(tmp_path / "static"))

    import app.main as main

    importlib.reload(main)
    return TestClient(main.app), main


def create_assistant(client: TestClient, **overrides) -> dict:
    payload = {
        "name": "JaiChat Study Assistant",
        "system_prompt": SYSTEM_PROMPT,
        "prompt_template": PROMPT_TEMPLATE,
        "retrieval_top_k": 4,
        "retrieval_threshold": 0.05,
        "chunk_strategy": "chars",
        "chunk_size": 300,
        "chunk_overlap": 0,
        "section_level": 2,
    }
    payload.update(overrides)
    response = client.post("/api/assistants", json=payload)
    assert response.status_code == 200
    return response.json()


def upload_documents(client: TestClient, assistant_id: str) -> dict:
    response = client.post(
        f"/api/assistants/{assistant_id}/documents",
        files=[
            (
                "files",
                (
                    "jaichat.txt",
                    "JaiChat is built with FastAPI, vanilla HTML, CSS, and JavaScript. "
                    "It demonstrates dynamic RAG with retrieved chunks.",
                    "text/plain",
                ),
            ),
            (
                "files",
                (
                    "recipe.txt",
                    "Pa amb tomaquet uses bread, tomato, olive oil, and salt.",
                    "text/plain",
                ),
            ),
        ],
    )
    assert response.status_code == 200
    return response.json()


def test_upload_ingests_documents_and_answer_shows_provenance(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path)
    assistant = create_assistant(client)
    upload_payload = upload_documents(client, assistant["id"])

    assert upload_payload["collection_count"] == 2
    assert len(upload_payload["documents"]) == 2
    assert all(document["doc_url"].startswith("/static/uploads/") for document in upload_payload["documents"])
    assert all(document["markdown_url"].startswith("/static/markdown/") for document in upload_payload["documents"])

    answer_response = client.post(
        f"/api/assistants/{assistant['id']}/chat",
        json={"user_input": "What is JaiChat built with?"},
    )
    assert answer_response.status_code == 200
    answer_payload = answer_response.json()

    assert "FastAPI" in answer_payload["reply"]
    assert answer_payload["provenance"]
    assert any(item["filename"] == "jaichat.txt" for item in answer_payload["provenance"])
    assert answer_payload["provenance"][0]["doc_url"].startswith("/static/uploads/")
    assert answer_payload["provenance"][0]["similarity"] is not None
    assert "{context}" not in answer_payload["debug"]["filled_prompt"]
    assert "chunk" in answer_payload["debug"]["filled_prompt"]
    assert answer_payload["debug"]["usage"]["prompt_tokens"] > 0
    assert answer_payload["debug"]["usage"]["completion_tokens"] > 0


def test_original_and_markdown_files_are_stored_under_static(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path)
    assistant = create_assistant(client)
    upload_payload = upload_documents(client, assistant["id"])

    for document in upload_payload["documents"]:
        original = tmp_path / "static" / document["doc_url"].removeprefix("/static/")
        markdown = tmp_path / "static" / document["markdown_url"].removeprefix("/static/")
        assert original.exists()
        assert markdown.exists()
        assert markdown.suffix == ".md"


def test_refuses_when_threshold_blocks_all_chunks(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path)
    assistant = create_assistant(client, retrieval_threshold=0.99)
    upload_documents(client, assistant["id"])

    response = client.post(
        f"/api/assistants/{assistant['id']}/chat",
        json={"user_input": "Who won Roland Garros 2026?"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["reply"] == "I do not know from the provided context."
    assert payload["provenance"] == []
    assert payload["debug"]["messages_sent"] == []
    assert payload["debug"]["usage"]["provider"] == "retrieval-gate"
    assert payload["debug"]["usage"]["prompt_tokens"] == 0


def test_top_k_limits_retrieved_provenance(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path)
    assistant = create_assistant(client, retrieval_top_k=1, retrieval_threshold=0.0)
    upload_documents(client, assistant["id"])

    response = client.post(
        f"/api/assistants/{assistant['id']}/chat",
        json={"user_input": "What is JaiChat built with?"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["provenance"]) == 1
    assert len(payload["debug"]["retrieved_chunks"]) == 1


def test_sections_chunking_strategy_is_configurable(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path)
    assistant = create_assistant(client, chunk_strategy="sections", section_level=2)

    response = client.post(
        f"/api/assistants/{assistant['id']}/documents",
        files={
            "files": (
                "notes.md",
                "# Course notes\n\n## EASY-RAG\nJaiChat retrieves chunks by meaning.\n\n## Tokens\nPrompt tokens drop when only chunks ride along.",
                "text/markdown",
            )
        },
    )
    assert response.status_code == 200
    document = response.json()["documents"][0]

    assert document["chunking_strategy"] == "sections(level=2)"
    assert document["inserted_count"] >= 2


def test_model_messages_keep_previous_history_bare(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path)
    assistant = create_assistant(client)
    upload_documents(client, assistant["id"])

    first = client.post(
        f"/api/assistants/{assistant['id']}/chat",
        json={"user_input": "What is JaiChat built with?"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/assistants/{assistant['id']}/chat",
        json={"user_input": "What does the recipe use?"},
    )
    assert second.status_code == 200
    messages = second.json()["debug"]["messages_sent"]

    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1] == {"role": "user", "content": "What is JaiChat built with?"}
    assert messages[2]["role"] == "assistant"
    assert "provenance" not in messages[2]
    assert messages[3]["role"] == "user"
    assert "Context:\n---\n[" in messages[3]["content"]
    assert "Question: What does the recipe use?" in messages[3]["content"]


def test_prompt_template_requires_rag_placeholders(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path)
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
