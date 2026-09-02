import json
from pathlib import Path
from typing import TypedDict

METADATA_PATH = Path(__file__).resolve().parents[2] / "data" / "metadata" / "papers.json"


class PaperMetadata(TypedDict):
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str  # ISO date string
    search_query: str | None
    """The arXiv search query that surfaced this paper during ingestion —
    None for papers backfilled via fetch_metadata_by_ids(), since that path
    looks up an existing paper_id directly and never had a query to begin
    with."""


def save_metadata(papers: list[PaperMetadata]) -> None:
    """Merges into the existing store rather than replacing it — corpus
    building now happens incrementally (one call per batch, potentially
    many batches over time), so overwriting the whole file here would
    silently drop every paper from a previous batch."""
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = load_metadata()
    existing.update({p["paper_id"]: p for p in papers})
    METADATA_PATH.write_text(json.dumps(existing, indent=2))


def load_metadata() -> dict[str, PaperMetadata]:
    if not METADATA_PATH.exists():
        return {}
    return json.loads(METADATA_PATH.read_text())


def get_paper(paper_id: str) -> PaperMetadata | None:
    return load_metadata().get(paper_id)
