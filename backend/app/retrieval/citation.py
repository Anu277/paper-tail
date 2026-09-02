from app.agent.state import Evidence
from app.knowledge.citation_graph import edges_from

# Real design constraint (flagged before building this): naive "fetch the
# cited paper, then follow its citations too" recurses effectively
# forever. edges_from() only ever looks at ONE paper's direct citations
# (never the cited paper's own references), so depth is inherently capped
# at 1 hop. This cap is the other half — a single traversal call can't
# return an unbounded number of citations either.
MAX_CITATIONS_PER_CALL = 3


def traverse(paper_id: str) -> list[Evidence]:
    """Fig.01 stage 6 — citation traversal.

    Lightweight version: surfaces WHAT paper_id cites as informational
    evidence (title + OpenAlex ID). Does NOT fetch, parse, or embed the
    cited paper's actual content — that paper stays outside our ingested
    corpus. Fetching and live-ingesting a cited paper on demand is a
    separate, bigger capability, not built here.
    """
    edges = edges_from(paper_id)[:MAX_CITATIONS_PER_CALL]
    return [
        Evidence(
            paper_id=paper_id,
            chunk_id=f"{paper_id}-cites-{i}",
            text=(
                f"This paper cites {edge['title']!r} ({edge['to_paper']}) — "
                "full text not in our corpus, title/ID only."
            ),
            section="References",
            source="citation",
        )
        for i, edge in enumerate(edges)
    ]
