import pickle
from pathlib import Path

from langchain_community.retrievers import BM25Retriever

INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "indexes" / "bm25" / "index.pkl"


def build_bm25(texts: list[str], metadatas: list[dict]) -> BM25Retriever:
    """metadatas[i] should carry provenance for texts[i] — same paper_id/
    chunk_id/section shape as the FAISS index, both built from the same
    app.ingestion.corpus.build_corpus() output.
    """
    return BM25Retriever.from_texts(texts, metadatas=metadatas)


def save_bm25(retriever: BM25Retriever) -> None:
    """rank_bm25's underlying model is just term-frequency tables — no GPU
    state, no live model handles — so a plain pickle is sufficient, unlike
    FAISS which needs its own native format for the index itself."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_bytes(pickle.dumps(retriever))


def load_bm25() -> BM25Retriever:
    return pickle.loads(INDEX_PATH.read_bytes())
