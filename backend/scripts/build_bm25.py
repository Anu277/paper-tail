"""Build the BM25 keyword index from every PDF in data/papers/raw/, using
the same GROBID-parsed, section-aware chunks as the FAISS index (both
consume app.ingestion.corpus.build_corpus() — GROBID only runs once).

Requires GROBID running: docker run -d --name grobid -p 8070:8070 grobid/grobid:0.8.1

Run: uv run python -m scripts.build_bm25
"""

from app.ingestion.corpus import build_corpus
from app.knowledge.bm25_store import build_bm25, save_bm25


def main() -> None:
    texts, metadatas = build_corpus()

    print(f"\nbuilt {len(texts)} chunks")

    retriever = build_bm25(texts, metadatas)
    save_bm25(retriever)
    print("BM25 index saved to data/indexes/bm25/")


if __name__ == "__main__":
    main()
