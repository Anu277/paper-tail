"""Backfill the metadata store for papers already in data/papers/raw/ —
those were ingested before this store existed, so their title/authors/
published date were fetched once by download.py but never saved.

Run: uv run python -m scripts.build_metadata
"""

from pathlib import Path

from app.ingestion.download import fetch_metadata_by_ids
from app.knowledge.metadata_store import save_metadata

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "papers" / "raw"


def main() -> None:
    paper_ids = [p.stem for p in sorted(RAW_DIR.glob("*.pdf"))]
    print(f"fetching metadata for {len(paper_ids)} papers: {paper_ids}")

    papers = fetch_metadata_by_ids(paper_ids)
    save_metadata(papers)

    for p in papers:
        print(f"  {p['paper_id']} | {p['published'][:10]} | {p['title'][:60]}")
    print(f"\nmetadata saved to data/metadata/papers.json ({len(papers)} papers)")


if __name__ == "__main__":
    main()
