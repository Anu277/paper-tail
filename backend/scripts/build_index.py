"""Build the FAISS vector index from every PDF in data/papers/raw/, using
GROBID for real section structure. Chunking happens WITHIN each section, so
a chunk can never straddle two different sections — see
parsing-comparison.html for why that matters.

Requires GROBID running: docker run -d --name grobid -p 8070:8070 grobid/grobid:0.8.1

Run: uv run python -m scripts.build_index
"""

from app.ingestion.corpus import build_corpus
from app.knowledge.vector_store import build_index, save_index


def main() -> None:
    texts, metadatas = build_corpus()

    print(f"\nbuilt {len(texts)} chunks")
    print("embedding (this is the slow part — progress bar below)...\n")

    index = build_index(texts, metadatas)
    save_index(index)
    print("\nindex saved to data/indexes/vector/")


if __name__ == "__main__":
    main()
