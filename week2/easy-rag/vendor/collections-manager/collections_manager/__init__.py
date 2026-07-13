# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""collections_manager — the simplest possible embeddings-database manager.

An embeddings database implements tables indexed with embeddings. We call these
tables COLLECTIONS. There are many implementations (open source, local, cloud);
this package is the whole idea reduced to three functions, on ChromaDB:

    create_collection(name, ...)            -> Collection   (in memory, or persisted on disk)
    insert(collection, chunk, metadata)     -> {"ok", "id", "error"}
    query(collection, query_text, top_k)    -> [{"chunk", "metadata", "similarity"|"distance"}, ...]

Basic metadata is at least `source` and `chunk_number` (within the source);
`chunk_number` is auto-assigned per source when you don't give one.

This is a provided utility, not a demo: build your applications against THIS
interface. Chroma is more than enough for small-to-medium projects (keep it
simple) — and because your code talks to this abstraction layer, you can swap
in a beefier engine later, if someone is happy to pay for it, without touching
the application code.
"""
import math
import os
from dataclasses import dataclass, field
from typing import Callable

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

__all__ = ["Collection", "create_collection", "insert", "query", "default_embedding_function"]

# The two metrics from the embeddings lecture, mapped to Chroma's index spaces.
# NOTE: Chroma's "l2" space returns SQUARED euclidean distance — we take the
# square root so `distance` means what the lecture said it means.
_METRICS = {"cosine": "cosine", "euclidean": "l2"}


def default_embedding_function(texts: list[str]) -> list[list[float]]:
    """Embed via any OpenAI-compatible endpoint (default: local Ollama + nomic-embed-text)."""
    client = OpenAI(
        base_url=os.environ.get("OPENAI_ENDPOINT", "http://localhost:11434/v1"),
        api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
    )
    model = os.environ.get("EMBED_MODEL", "nomic-embed-text")
    resp = client.embeddings.create(model=model, input=texts)
    return [row.embedding for row in resp.data]


@dataclass
class Collection:
    """A handle to one collection: its Chroma table + how to embed + how to measure."""
    name: str
    description: str
    metric: str  # "cosine" | "euclidean"
    embedding_function: Callable[[list[str]], list[list[float]]]
    _chroma: "chromadb.Collection" = field(repr=False)

    def count(self) -> int:
        return self._chroma.count()


def create_collection(
    name: str,
    embedding_function: Callable[[list[str]], list[list[float]]] | None = None,
    description: str = "",
    metric: str = "cosine",
    persist_path: str | None = None,
) -> Collection:
    """Create (or re-open) a collection.

    With `persist_path` the collection lives on disk at that folder and survives
    restarts; without it, it lives in memory for this run. `metric` is "cosine"
    (higher = closer) or "euclidean" (lower = closer). If you don't pass an
    `embedding_function`, the default one (OpenAI-compatible endpoint from .env)
    is used — everything inserted into one collection MUST be embedded by the
    same model, or the geometry means nothing.
    """
    if metric not in _METRICS:
        raise ValueError(f"metric must be one of {list(_METRICS)}, got {metric!r}")
    client = chromadb.PersistentClient(path=persist_path) if persist_path else chromadb.EphemeralClient()
    chroma_col = client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": _METRICS[metric], "description": description},
    )
    return Collection(
        name=name,
        description=description,
        metric=metric,
        embedding_function=embedding_function or default_embedding_function,
        _chroma=chroma_col,
    )


def insert(collection: Collection, chunk: str, metadata: dict) -> dict:
    """Insert one chunk with its metadata. Returns an ok/ko message.

    `metadata` must carry at least `source` (where the chunk comes from).
    `chunk_number` (position within that source) is auto-assigned — the next
    free number for that source — unless you provide it. The chunk's id is
    "<source>::<chunk_number>", so re-inserting the same position fails
    cleanly instead of silently duplicating.
    """
    if not chunk or not chunk.strip():
        return {"ok": False, "id": None, "error": "empty chunk"}
    if "source" not in metadata:
        return {"ok": False, "id": None, "error": "metadata must include 'source'"}
    meta = dict(metadata)
    if "chunk_number" not in meta:
        existing = collection._chroma.get(where={"source": meta["source"]})
        taken = [m.get("chunk_number", -1) for m in existing["metadatas"]]
        meta["chunk_number"] = (max(taken) + 1) if taken else 0
    chunk_id = f"{meta['source']}::{meta['chunk_number']}"
    if collection._chroma.get(ids=[chunk_id])["ids"]:
        # Chroma's add() silently skips existing ids — check explicitly so ko means ko.
        return {"ok": False, "id": chunk_id, "error": f"id {chunk_id!r} already exists"}
    try:
        [vector] = collection.embedding_function([chunk])
        collection._chroma.add(ids=[chunk_id], embeddings=[vector], documents=[chunk], metadatas=[meta])
        return {"ok": True, "id": chunk_id, "error": None}
    except Exception as e:  # embeddings endpoint down, ...
        return {"ok": False, "id": chunk_id, "error": str(e)}


def query(collection: Collection, query_text: str, top_k: int = 3, threshold: float | None = None) -> list[dict]:
    """Retrieve the nearest chunks to `query_text`, nearest first.

    Each result is {"chunk", "metadata", and "similarity" (cosine, higher =
    closer) or "distance" (euclidean, lower = closer)}. `threshold` filters:
    minimum similarity for cosine, maximum distance for euclidean.
    """
    if collection.count() == 0:
        return []
    [query_vector] = collection.embedding_function([query_text])
    hits = collection._chroma.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    results = []
    for chunk, meta, dist in zip(hits["documents"][0], hits["metadatas"][0], hits["distances"][0]):
        if collection.metric == "cosine":
            score_name, score = "similarity", 1.0 - dist          # chroma cosine returns 1 - cos_sim
            if threshold is not None and score < threshold:
                continue
        else:
            score_name, score = "distance", math.sqrt(dist)       # chroma l2 returns SQUARED distance
            if threshold is not None and score > threshold:
                continue
        results.append({"chunk": chunk, "metadata": meta, score_name: round(score, 4)})
    return results
