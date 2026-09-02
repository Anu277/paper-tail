import operator
from typing import Annotated, Literal, TypedDict


class Evidence(TypedDict):
    paper_id: str
    chunk_id: str
    text: str
    section: str
    source: Literal["semantic", "bm25", "citation"]


class Claim(TypedDict):
    text: str
    paper_id: str


class ResearchState(TypedDict):
    """The Research Workspace — Fig.01 stage 2.

    Written by the evaluator (stage 7), read by the decision node (stage 8),
    and read/updated by the agent (stage 1) across every loop iteration.
    This is shared memory, not a value any single node owns.
    """

    question: str
    sub_questions: list[str]
    search_history: Annotated[list[str], operator.add]
    search_methods: list[Literal["semantic", "bm25"]]
    year_from: int | None
    year_to: int | None
    evidence: Annotated[list[Evidence], operator.add]
    claims: list[Claim]
    claims_by_paper: dict[str, list[str]]
    contradictions: list[str]
    missing: list[str]
    iteration: int
    intent: Literal["research", "greeting", "off_topic", ""]
    """Set once, by the very first node (intent_node) — classifies the
    incoming message before any search happens. 'greeting' gets a light
    reply; 'off_topic' gets a firm scoped refusal, NOT an answer from the
    model's own knowledge — deliberately strict so this can't be used as
    an open-ended general assistant / prompt-injection surface. Both
    short-circuit straight to END with final_report already set;
    'research' proceeds into the normal planner loop."""
    decision: Literal["enough", "missing", "conflict", "need_source_context", ""]
    target_paper_id: str | None
    final_report: str
    trace: str
    """One-line human-readable summary of what the node that just ran did —
    same text as that node's own print() line (decision_node is the one
    exception: here it holds just the reasoning sentence, since decision/
    target_paper_id are already their own state fields). No reducer: each
    node overwrites it with its own line; read once per node by the
    /research/stream route to build that node's trace-timeline caption."""
