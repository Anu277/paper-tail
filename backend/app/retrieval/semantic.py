from app.agent.state import Evidence
from app.knowledge.vector_store import load_index


def search(query: str, k: int = 4) -> list[Evidence]:
    """Fig.01 stage 4.1 — semantic search over the vector index."""
    index = load_index()
    results = index.similarity_search(query, k=k)
    return [
        Evidence(
            paper_id=doc.metadata["paper_id"],
            chunk_id=doc.metadata["chunk_id"],
            text=doc.page_content,
            section=doc.metadata.get("section", ""),
            source="semantic",
        )
        for doc in results
    ]
