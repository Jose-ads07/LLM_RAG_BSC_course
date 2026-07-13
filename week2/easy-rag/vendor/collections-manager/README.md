<!-- =============================================================================================================== -->
<!-- Universitat Politècnica de Catalunya (UPC)                                                                      -->
<!-- =============================================================================================================== -->

# 🗂️ Collections Manager

**A provided utility, not a demo.** An embeddings database implements tables indexed
with embeddings — we call these tables **collections**. There are many implementations
out there; this package is the whole idea reduced to **three functions**, implemented
on [ChromaDB](https://www.trychroma.com/):

```python
from collections_manager import create_collection, insert, query

col = create_collection("handbook", description="Acme's product docs",
                        metric="cosine", persist_path="./my-collections")

insert(col, "The Pallet Pup has a top speed of 2.4 m/s.", {"source": "acme-handbook"})
# -> {"ok": True, "id": "acme-handbook::0", "error": None}

query(col, "how quick is the delivery robot?", top_k=3)
# -> [{"chunk": "...", "metadata": {"source": "acme-handbook", "chunk_number": 0},
#      "similarity": 0.71}, ...]
```

## The API

| Function | What it does |
|---|---|
| `create_collection(name, embedding_function=None, description="", metric="cosine", persist_path=None)` | Create — or re-open — a collection. With `persist_path` it lives on disk and survives restarts; without, in memory. `metric` is `"cosine"` (higher = closer) or `"euclidean"` (lower = closer). |
| `insert(collection, chunk, metadata)` | Store one chunk. Returns `{"ok", "id", "error"}`. Metadata must carry at least `source`; `chunk_number` (position within the source) is auto-assigned if absent. Ids are `source::chunk_number`, so re-inserting a position fails cleanly. |
| `query(collection, query_text, top_k=3, threshold=None)` | The nearest chunks, nearest first, each with its metadata and its `similarity` (cosine) or `distance` (euclidean). `threshold` = min similarity / max distance. |

The default embedding function calls any OpenAI-compatible endpoint (from `.env`:
`OPENAI_ENDPOINT`, `EMBED_MODEL`, `OPENAI_API_KEY` — default local Ollama +
`nomic-embed-text`, no key, no cost). You can pass your own
`embedding_function(list[str]) -> list[list[float]]`. One rule: everything in a
collection must be embedded by the **same model**, or the geometry means nothing.

## Why an abstraction layer

For most small-to-medium projects, Chroma is more than enough — keep it simple.
But requirements grow. Because your application talks to *this* interface and not
to Chroma directly, you can swap the engine underneath — pgvector, a managed cloud
store, whatever someone is happy to pay for — by rewriting one small file, not
your application.

## Use it from your own project

Add it as a path dependency in your `pyproject.toml`:

```toml
dependencies = ["collections-manager"]

[tool.uv.sources]
collections-manager = { path = "../../collections-manager", editable = true }
```

(Adjust the relative path. See `week-02/demos/04-collections-explorer/` for a working example.)

## 📖 License

Licensed under [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (`CC BY-NC-SA 4.0`).

## 👤 Author

[@granludo](https://github.com/granludo) — Marc Alier, Universitat Politècnica de Catalunya (UPC)
