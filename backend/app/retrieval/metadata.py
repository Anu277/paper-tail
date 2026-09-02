from app.agent.state import Evidence
from app.knowledge.metadata_store import load_metadata


def filter_by_year(evidence: list[Evidence], year_from: int | None, year_to: int | None) -> list[Evidence]:
    """Fig.01 stage 4.3 — metadata filter.

    Not a standalone search (a year range alone returns nothing meaningful
    without a query) — a peer control applied to whatever semantic/bm25
    already found, same as the architecture doc's "filters can apply
    before, during, or after retrieval" note. Drops evidence whose paper
    falls outside the range; evidence for a paper_id missing from the
    metadata store is kept rather than silently dropped, since an absent
    year isn't evidence the paper falls outside the range.
    """
    if year_from is None and year_to is None:
        return evidence

    papers = load_metadata()
    kept = []
    for e in evidence:
        paper = papers.get(e["paper_id"])
        if paper is None:
            kept.append(e)
            continue
        year = int(paper["published"][:4])
        if year_from is not None and year < year_from:
            continue
        if year_to is not None and year > year_to:
            continue
        kept.append(e)
    return kept
