"""Build the citation graph: for each paper, resolve its GROBID-parsed
references to real OpenAlex work IDs and save the edges.

Requires GROBID running: docker run -d --name grobid -p 8070:8070 grobid/grobid:0.8.1

Run: uv run python -m scripts.build_citation_graph
"""

from pathlib import Path

from app.ingestion.parser import parse_pdf
from app.ingestion.references import resolve_reference
from app.knowledge.citation_graph import CitationEdge, save_graph

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "papers" / "raw"


def main() -> None:
    edges: list[CitationEdge] = []

    for pdf_path in sorted(RAW_DIR.glob("*.pdf")):
        paper_id = pdf_path.stem
        paper = parse_pdf(str(pdf_path))
        print(f"[refs] {paper_id}: {len(paper['references'])} references to resolve")

        resolved_count = 0
        for ref in paper["references"]:
            resolved_id = resolve_reference(ref["title"])
            if resolved_id:
                edges.append({"from_paper": paper_id, "to_paper": resolved_id, "title": ref["title"]})
                resolved_count += 1
                print(f"  {ref['title'][:60]!r} -> {resolved_id}")
            else:
                print(f"  {ref['title'][:60]!r} — no match found")

        print(f"  resolved {resolved_count}/{len(paper['references'])}\n")

    save_graph(edges)
    print(f"citation graph saved: {len(edges)} total edges -> data/citation_graph/graph.json")


if __name__ == "__main__":
    main()
