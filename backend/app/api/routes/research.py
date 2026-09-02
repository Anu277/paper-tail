import json
import uuid
from functools import lru_cache

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agent.graph import build_graph
from app.api.schemas import ClaimResponse, ResearchRequest, ResearchResponse

router = APIRouter()


@lru_cache
def get_compiled_graph():
    return build_graph()


def _initial_state(question: str) -> dict:
    return {
        "question": question,
        "sub_questions": [],
        "search_history": [],
        "search_methods": [],
        "year_from": None,
        "year_to": None,
        "evidence": [],
        "claims": [],
        "claims_by_paper": {},
        "contradictions": [],
        "missing": [],
        "iteration": 0,
        "intent": "",
        "decision": "",
        "target_paper_id": None,
        "final_report": "",
        "trace": "",
    }


@router.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest) -> ResearchResponse:
    """Runs a question through the full agent loop — plan, retrieve, evaluate,
    decide (looping up to MAX_ITERATIONS), verify, answer. Blocking: a real
    run takes 2-3 minutes (multiple Groq calls per loop iteration). Real
    streaming to the frontend is a later design piece, not this endpoint.
    """
    graph = get_compiled_graph()
    final_state = graph.invoke(_initial_state(request.question))
    return ResearchResponse(
        question=request.question,
        final_report=final_state["final_report"],
        claims=[ClaimResponse(**c) for c in final_state["claims"]],
        claims_by_paper=final_state["claims_by_paper"],
        search_history=final_state["search_history"],
        iterations=final_state["iteration"],
        decision=final_state["decision"],
    )


# node name (as registered in graph.py) -> NodeKind the frontend understands
# (app/agent/nodes.py's node names don't all match 1:1 with the frontend's
# NodeKind union — "evaluate"/"decide" here become "evaluator"/"decision"
# there, see frontend/src/lib/agent-stream.ts).
_NODE_KIND: dict[str, str] = {
    "intent": "intent",
    "planner": "planner",
    "retrieve": "retrieve",
    "evaluate": "evaluator",
    "decide": "decision",
    "citation": "citation",
    "verify": "verify",
    "answer": "answer",
}
_NODE_LABEL: dict[str, str] = {
    "intent": "Understanding message",
    "planner": "Planner",
    "retrieve": "Retrieve",
    "evaluator": "Evaluate",
    "decision": "Decide",
    "citation": "Citation traversal",
    "verify": "Verify",
    "answer": "Answer",
}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _stream_events(question: str):
    graph = get_compiled_graph()
    # Display-iteration counter: starts at 1, bumped right after a "decide"
    # step (using the real iteration count decision_node itself just
    # returned, +1) so every step that follows — whether the graph looped
    # back to the planner or took the citation detour — is grouped under
    # the new round. decide's own step stays tagged with the round it was
    # deciding for, not the round it just kicked off.
    iteration = 1
    try:
        for chunk in graph.stream(_initial_state(question), stream_mode="updates"):
            node_name, delta = next(iter(chunk.items()))
            kind = _NODE_KIND[node_name]

            if kind == "decision":
                caption: str | None = delta["decision"]
                if delta.get("target_paper_id"):
                    caption += f" → {delta['target_paper_id']}"
                detail = delta.get("trace") or None
            else:
                caption = delta.get("trace") or None
                detail = None

            yield _sse({
                "type": "step",
                "step": {
                    "id": str(uuid.uuid4()),
                    "node": kind,
                    "label": _NODE_LABEL[kind],
                    "iteration": iteration,
                    "caption": caption,
                    "detail": detail,
                },
            })

            if kind == "decision":
                iteration = delta["iteration"] + 1

            # answer_node is the normal path; intent_node's chitchat
            # shortcut also sets final_report directly and skips straight
            # to END (see route_after_intent in graph.py) — either way,
            # a real final_report showing up IS the answer to surface.
            if delta.get("final_report"):
                yield _sse({"type": "answer", "markdown": delta["final_report"]})

        yield _sse({"type": "done"})
    except Exception as e:  # noqa: BLE001 — any failure must reach the client as a real SSE event, not a silently dropped connection
        yield _sse({"type": "error", "message": str(e)})


@router.post("/research/stream")
def research_stream(request: ResearchRequest) -> StreamingResponse:
    """Same agent loop as POST /research, but pushed to the client as one
    SSE event per completed LangGraph node instead of a single blocking
    JSON response — see FRONTEND_UI_DESIGN.md section 5 for why this
    exists. Every field in each event is real data returned by the node
    that just ran (nodes.py's own `trace` field, or `decision`/
    `target_paper_id` already in state) — nothing here is synthesized.
    """
    return StreamingResponse(
        _stream_events(request.question), media_type="text/event-stream"
    )
