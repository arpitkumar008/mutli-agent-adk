
"""RAG: load policies -> chunk per policy ID -> embed -> store in ChromaDB."""
import re
import chromadb
from google import genai
from google.genai import types
from pypdf import PdfReader

from .config import CHROMA_DIR, COLLECTION, EMBED_MODEL, POLICY_DIR, TOP_K

_client = None

def _genai():
    global _client
    if _client is None:
        _client = genai.Client()  
    return _client


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    out = []
    for i in range(0, len(texts), 50):
        res = _genai().models.embed_content(
            model=EMBED_MODEL,
            contents=texts[i:i + 50],
            config=types.EmbedContentConfig(task_type=task_type),
        )
        out.extend(e.values for e in res.embeddings)
    return out


def _collection():
    db = chromadb.PersistentClient(path=CHROMA_DIR)
    return db.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def _read_file(path) -> str:
    if path.suffix.lower() == ".pdf":
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8")


HEADER = re.compile(r"^\s*POLICY\s+([A-Z]{2,6}-\d{1,4})\s*[:\-–]\s*(.*)$", re.MULTILINE)


def chunk_by_policy(text: str, source: str) -> list[dict]:
    """One chunk per policy ID."""
    matches = list(HEADER.finditer(text))
    chunks = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunks.append({
            "policy_id": m.group(1),
            "title": m.group(2).strip(),
            "text": text[m.start():end].strip(),
            "source": source,
        })
    return chunks


def ingest_policies() -> int:
    chunks = []
    for f in sorted(POLICY_DIR.glob("*")):
        if f.suffix.lower() in {".pdf", ".md", ".txt"}:
            chunks += chunk_by_policy(_read_file(f), f.name)
    if not chunks:
        raise RuntimeError(f"No 'POLICY <ID>: <title>' sections found in {POLICY_DIR}")

    col = _collection()
    existing = col.get()["ids"]
    if existing:
        col.delete(ids=existing)  

    docs = [c["text"] for c in chunks]
    col.add(
        ids=[c["policy_id"] for c in chunks],  # embedding keyed by policy ID
        documents=docs,
        embeddings=_embed(docs, "RETRIEVAL_DOCUMENT"),
        metadatas=[{"policy_id": c["policy_id"], "title": c["title"], "source": c["source"]}
                   for c in chunks],
    )
    return len(chunks)


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    col = _collection()
    n = col.count()
    if n == 0:
        return []
    res = col.query(query_embeddings=_embed([query], "RETRIEVAL_QUERY"),
                    n_results=min(k, n))
    return [
        {"policy_id": res["ids"][0][i],
         "title": res["metadatas"][0][i]["title"],
         "text": res["documents"][0][i],
         "distance": res["distances"][0][i]}
        for i in range(len(res["ids"][0]))
    ]


def policy_map() -> dict[str, dict]:
    """Ground truth {policy_id: {title, text}} straight from the DB (for the verifier)."""
    data = _collection().get()
    return {pid: {"title": meta["title"], "text": doc}
            for pid, meta, doc in zip(data["ids"], data["metadatas"], data["documents"])}


def count() -> int:
    return _collection().count()