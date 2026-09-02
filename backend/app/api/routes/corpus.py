import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.schemas import CorpusBuildRequest, CorpusPaper, CorpusResponse
from app.ingestion.pipeline import run_ingestion
from app.knowledge.metadata_store import load_metadata

router = APIRouter()


@router.get("/corpus", response_model=CorpusResponse)
def corpus() -> CorpusResponse:
    """Lists every ingested paper with the search query that brought it in
    — lets the frontend show what keywords the corpus was actually built
    on, grouped by paper, not just a flat unlabeled title list."""
    papers = load_metadata()
    return CorpusResponse(
        papers=[
            CorpusPaper(
                paper_id=p["paper_id"],
                title=p["title"],
                published=p["published"],
                search_query=p.get("search_query"),
            )
            for p in papers.values()
        ]
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _corpus_build_events(topic: str, count: int):
    try:
        for item in run_ingestion(topic, count):
            if "summary" in item:
                yield _sse({"type": "summary", "text": item["summary"]})
            else:
                yield _sse({"type": "stage", "stage": item})
        yield _sse({"type": "done"})
    except Exception as e:  # noqa: BLE001 — any failure must reach the client as a real SSE event
        yield _sse({"type": "error", "message": str(e)})


@router.post("/corpus/build/stream")
def corpus_build_stream(request: CorpusBuildRequest) -> StreamingResponse:
    """Runs the real ingestion pipeline (search -> download -> parse ->
    chunk -> embed -> index -> bm25 -> citations -> metadata), pushing one
    SSE event per stage update — matches frontend/src/lib/corpus-stream.ts's
    CorpusEvent shape exactly. See app/ingestion/pipeline.py for the actual
    work; this route is just the SSE wrapper around it.
    """
    return StreamingResponse(
        _corpus_build_events(request.topic, request.count), media_type="text/event-stream"
    )
