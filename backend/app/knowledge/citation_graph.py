import json
from pathlib import Path
from typing import TypedDict

GRAPH_PATH = Path(__file__).resolve().parents[2] / "data" / "citation_graph" / "graph.json"


class CitationEdge(TypedDict):
    from_paper: str
    to_paper: str  # OpenAlex work ID
    title: str  # the cited paper's title, for human-readable debugging


def save_graph(edges: list[CitationEdge]) -> None:
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_PATH.write_text(json.dumps(edges, indent=2))


def load_graph() -> list[CitationEdge]:
    if not GRAPH_PATH.exists():
        return []
    return json.loads(GRAPH_PATH.read_text())


def edges_from(paper_id: str) -> list[CitationEdge]:
    """What paper_id cites — used by stage 6 citation traversal."""
    return [e for e in load_graph() if e["from_paper"] == paper_id]
