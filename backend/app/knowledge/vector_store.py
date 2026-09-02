from functools import lru_cache
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "indexes" / "vector"
# Switched from all-MiniLM-L6-v2 (max_seq_length=256) after proving it
# silently truncated our ~650-token chunks: two texts sharing a 641-token
# prefix but with completely different endings produced cosine similarity
# 0.9999999999999998 — the model never saw the endings at all. BGE-M3
# supports 8192 tokens (verified: same test gives 0.94, a real difference)
# so full chunks embed without truncation, no need to shrink chunk size
# to fit a small model's limit.
EMBEDDING_MODEL = "BAAI/bge-m3"


@lru_cache
def get_embeddings() -> HuggingFaceEmbeddings:
    # BGE-M3 (568M params) OOMs on this machine's GPU (3.64GB VRAM total) —
    # MiniLM (22M params) was small enough to fit, BGE-M3 isn't. Corpus is
    # small enough (currently 5 papers, ~200 planned) that CPU embedding is
    # still entirely practical, just slower than GPU would be.
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        show_progress=True,
    )


def build_index(texts: list[str], metadatas: list[dict]) -> FAISS:
    """metadatas[i] should carry provenance for texts[i] — paper_id, chunk_id."""
    return FAISS.from_texts(texts, get_embeddings(), metadatas=metadatas)


def save_index(index: FAISS) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    index.save_local(str(INDEX_DIR))


def load_index() -> FAISS:
    return FAISS.load_local(
        str(INDEX_DIR),
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )
