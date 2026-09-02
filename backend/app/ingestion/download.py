import re
from pathlib import Path

import arxiv
import requests

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "papers" / "raw"


def _strip_version(short_id: str) -> str:
    """arxiv.get_short_id() returns e.g. '2506.06962v3' for a modern ID, or
    the pre-2007 format 'cond-mat/0608423v1' for an older one. Strip the
    version suffix (so citation matching isn't thrown off by which version
    we fetched) AND replace the old format's '/' with '_' — paper_id is
    used as a filename (data/papers/raw/{id}.pdf) and a dict key everywhere
    else in this codebase, and a literal '/' there is a path separator, not
    part of the name. Real failure hit: 'cond-mat/0608423' tried to write
    into a non-existent 'cond-mat/' subdirectory and crashed with
    FileNotFoundError instead of just naming the file 'cond-mat_0608423.pdf'.
    """
    no_version = re.sub(r"v\d+$", "", short_id)
    return no_version.replace("/", "_")


def _result_to_metadata(result, pdf_path: Path, search_query: str | None = None) -> dict:
    return {
        "paper_id": _strip_version(result.get_short_id()),
        "title": result.title,
        "authors": [a.name for a in result.authors],
        "abstract": result.summary,
        "published": result.published.isoformat(),
        "pdf_path": str(pdf_path),
        "search_query": search_query,
    }


def search_papers(query: str, max_results: int) -> list[arxiv.Result]:
    """Just the arXiv search, no downloading — materialized into a real
    list (not left as arxiv's lazy generator) so a caller can report a
    real "N papers found" count before any download starts. Split out of
    fetch_papers() for scripts/pipeline.py's per-stage progress reporting.
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    return list(client.results(search))


def already_downloaded(result: arxiv.Result) -> bool:
    """Whether this paper's PDF is already on disk from an earlier fetch —
    lets a caller tell a genuinely new paper apart from one just re-surfaced
    by a later, different search, so it doesn't get re-counted as new or
    have its original search_query silently overwritten."""
    paper_id = _strip_version(result.get_short_id())
    return (RAW_DIR / f"{paper_id}.pdf").exists()


def download_paper(result: arxiv.Result, search_query: str | None = None) -> dict:
    """Downloads one paper's PDF (skips if already present) and returns
    its metadata dict."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    paper_id = _strip_version(result.get_short_id())
    pdf_path = RAW_DIR / f"{paper_id}.pdf"

    if not pdf_path.exists():
        response = requests.get(result.pdf_url, timeout=30)
        response.raise_for_status()
        # Belt-and-suspenders alongside _strip_version()'s "/" -> "_" fix
        # above: Path.write_bytes() does NOT create missing parent
        # directories on its own (that's what actually crashed on
        # 'cond-mat/0608423' before that fix existed) — this makes a
        # missing directory a non-issue even if some future paper_id
        # source ever produces a nested path again.
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(response.content)

    return _result_to_metadata(result, pdf_path, search_query=search_query)


def fetch_papers(query: str, max_results: int) -> list[dict]:
    """Search arXiv and download each paper's PDF to data/papers/raw/.

    Returns a list of metadata dicts (paper_id, title, authors, abstract,
    published, pdf_path) — one per paper actually downloaded.
    """
    results = search_papers(query, max_results)
    return [download_paper(r, search_query=query) for r in results]


def fetch_metadata_by_ids(paper_ids: list[str]) -> list[dict]:
    """Looks up existing papers by their exact arXiv ID — for backfilling
    metadata (title/authors/published) for papers already downloaded via
    fetch_papers(), without re-searching or re-downloading the PDF. Used
    once to populate the metadata store for papers ingested before that
    store existed.
    """
    client = arxiv.Client()
    search = arxiv.Search(id_list=paper_ids)
    return [
        _result_to_metadata(result, RAW_DIR / f"{_strip_version(result.get_short_id())}.pdf")
        for result in client.results(search)
    ]
