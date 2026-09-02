from app.agent.state import Evidence
from app.knowledge.bm25_store import load_bm25


def search(query: str, k: int = 4) -> list[Evidence]:
    """Fig.01 stage 4.2 — BM25 keyword search over the same chunks as
    semantic.py, best for exact terms/IDs/codes rather than paraphrase."""
    retriever = load_bm25()
    retriever.k = k
    results = retriever.invoke(query)
    return [
        Evidence(
            paper_id=doc.metadata["paper_id"],
            chunk_id=doc.metadata["chunk_id"],
            text=doc.page_content,
            section=doc.metadata.get("section", ""),
            source="bm25",
        )
        for doc in results
    ]
