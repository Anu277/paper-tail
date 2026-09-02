from pathlib import Path

from langchain_community.vectorstores import FAISS

from app.ingestion.chunker import chunk_text
from app.ingestion.download import already_downloaded, download_paper, search_papers
from app.ingestion.parser import parse_pdf
from app.ingestion.query_refiner import refine_search_query
from app.ingestion.references import resolve_reference
from app.knowledge.bm25_store import build_bm25, save_bm25
from app.knowledge.citation_graph import CitationEdge, save_graph
from app.knowledge.metadata_store import save_metadata
from app.knowledge.vector_store import get_embeddings, save_index

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "papers" / "raw"
EMBED_BATCH_SIZE = 16


def run_ingestion(topic: str, count: int):
    """Generator yielding one progress dict per pipeline step, consumed by
    POST /corpus/build/stream. Mirrors scripts/build_index.py + build_bm25.py
    + build_citation_graph.py + build_metadata.py, run from one UI-triggered
    call instead of four separate manual invocations, instrumented for real
    (not simulated) progress throughout.

    Each yielded dict is either a stage update — {"id": <StageId>,
    "status": ..., "current"?, "total"?, "note"?} matching the frontend's
    StageState shape directly — or a final {"summary": "..."} once
    everything is done. The route layer (app/api/routes/corpus.py) just
    wraps each into an SSE frame, no further transformation needed.

    Full-rebuild semantics, matching those scripts: every call reprocesses
    ALL PDFs in data/papers/raw/, not just the newly-fetched ones — GROBID
    parsing/chunking/embedding/citation-resolution all re-run for the whole
    corpus each time. Consistent with the existing design (those scripts
    already do this), not a regression; incremental-only reprocessing for
    just the new batch is a separate, unbuilt optimization.
    """
    # --- search ---
    # arXiv's search does literal term matching, not language understanding
    # — proved empirically that a raw sentence like "i want about quantum
    # computing" returns totally unrelated results. refine_search_query()
    # strips it to real keywords first.
    yield {"id": "search", "status": "active"}
    refined_query = refine_search_query(topic)
    results = search_papers(refined_query, count)
    # Checked up front (cheap filesystem check, no network) so both the
    # search note and the per-file download progress can honestly say
    # which results are actually new — a paper resurfaced by a later,
    # different search is NOT new, and must not have its original
    # search_query overwritten with this one.
    already_have = [already_downloaded(r) for r in results]
    new_count = already_have.count(False)
    yield {
        "id": "search",
        "status": "done",
        "note": f'{len(results)} found for "{refined_query}" ({new_count} new)',
    }

    # --- download ---
    yield {"id": "download", "status": "active", "total": len(results)}
    new_papers: list[dict] = []
    for i, (result, was_present) in enumerate(zip(results, already_have), start=1):
        metadata = download_paper(result, search_query=refined_query)
        if not was_present:
            new_papers.append(metadata)
        yield {
            "id": "download",
            "status": "active",
            "current": i,
            "total": len(results),
            "note": "already have this one" if was_present else None,
        }
    yield {"id": "download", "status": "done", "current": len(results), "total": len(results)}

    if not new_papers:
        # Nothing new was actually added — reprocessing the entire existing
        # corpus (parse/chunk/embed/index/bm25/citations) would be pure
        # waste, not just slow, since none of that output would change.
        yield {"summary": f'No new papers for "{refined_query}" — already had all {len(results)}.'}
        return

    # --- parse (GROBID) --- one parse_pdf() call per paper gets BOTH
    # sections (for chunking) and references (for citations) — the old
    # scripts each parsed every PDF separately for one or the other,
    # duplicating the slowest step in the whole pipeline.
    pdf_paths = sorted(RAW_DIR.glob("*.pdf"))
    yield {"id": "parse", "status": "active", "total": len(pdf_paths)}
    parsed_papers: list[tuple[str, dict]] = []
    for i, pdf_path in enumerate(pdf_paths, start=1):
        parsed_papers.append((pdf_path.stem, parse_pdf(str(pdf_path))))
        yield {"id": "parse", "status": "active", "current": i, "total": len(pdf_paths)}
    yield {"id": "parse", "status": "done", "current": len(pdf_paths), "total": len(pdf_paths)}

    # --- chunk ---
    yield {"id": "chunk", "status": "active", "total": len(parsed_papers)}
    texts: list[str] = []
    metadatas: list[dict] = []
    for i, (paper_id, parsed) in enumerate(parsed_papers, start=1):
        chunk_index = 0
        for section in parsed["sections"]:
            for chunk in chunk_text(section["text"]):
                texts.append(chunk)
                metadatas.append(
                    {
                        "paper_id": paper_id,
                        "chunk_id": f"{paper_id}-{chunk_index}",
                        "section": section["heading"],
                    }
                )
                chunk_index += 1
        yield {"id": "chunk", "status": "active", "current": i, "total": len(parsed_papers)}
    yield {
        "id": "chunk",
        "status": "done",
        "current": len(parsed_papers),
        "total": len(parsed_papers),
        "note": f"{len(texts)} chunks",
    }

    # --- embed --- the genuinely slow step, batched by hand so progress is
    # real rather than a spinner faking activity for however long it takes.
    embeddings = get_embeddings()
    yield {"id": "embed", "status": "active", "total": len(texts)}
    text_embedding_pairs: list[tuple[str, list[float]]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        vectors = embeddings.embed_documents(batch)
        text_embedding_pairs.extend(zip(batch, vectors))
        yield {
            "id": "embed",
            "status": "active",
            "current": min(start + EMBED_BATCH_SIZE, len(texts)),
            "total": len(texts),
        }
    yield {"id": "embed", "status": "done", "current": len(texts), "total": len(texts)}

    # --- index ---
    yield {"id": "index", "status": "active"}
    save_index(FAISS.from_embeddings(text_embedding_pairs, embeddings, metadatas=metadatas))
    yield {"id": "index", "status": "done"}

    # --- bm25 ---
    yield {"id": "bm25", "status": "active"}
    save_bm25(build_bm25(texts, metadatas))
    yield {"id": "bm25", "status": "done"}

    # --- citations ---
    all_refs = [
        (paper_id, ref) for paper_id, parsed in parsed_papers for ref in parsed["references"]
    ]
    yield {"id": "citations", "status": "active", "total": len(all_refs)}
    edges: list[CitationEdge] = []
    for i, (paper_id, ref) in enumerate(all_refs, start=1):
        resolved_id = resolve_reference(ref["title"])
        if resolved_id:
            edges.append({"from_paper": paper_id, "to_paper": resolved_id, "title": ref["title"]})
        yield {"id": "citations", "status": "active", "current": i, "total": len(all_refs)}
    save_graph(edges)
    yield {
        "id": "citations",
        "status": "done",
        "current": len(all_refs),
        "total": len(all_refs),
        "note": f"{len(edges)} edges resolved",
    }

    # --- metadata ---
    yield {"id": "metadata", "status": "active"}
    save_metadata(new_papers)
    yield {"id": "metadata", "status": "done"}

    yield {
        "summary": (
            f"{len(new_papers)} new papers, {len(texts)} chunks, {len(edges)} citation edges"
        )
    }
