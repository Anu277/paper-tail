from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    answer_node,
    citation_node,
    decision_node,
    evaluator_node,
    intent_node,
    planner_node,
    retrieve_node,
    verify_node,
)
from app.agent.state import ResearchState

MAX_ITERATIONS = 3  # safety cap — real stopping logic is decision_node's job,
# this only exists so a stuck "missing" loop can't burn API calls forever.
# Also caps citation-traversal detours: decision_node increments iteration
# every time it runs, need_source_context -> citation -> evaluate -> decide
# included, so a loop that keeps picking need_source_context still hits
# this same cap rather than looping forever.


def route_after_intent(state: ResearchState) -> str:
    """chitchat already has its final_report set by intent_node itself —
    skip straight to END rather than through answer_node, which expects
    real verified claims to write a report from."""
    return "planner" if state["intent"] == "research" else END


def route_after_decision(state: ResearchState) -> str:
    """Fig.01 stage 8 routing.

    enough -> verify -> answer. missing/conflict -> back to the planner for
    another round. need_source_context -> citation traversal (stage 6),
    which loops back to re-evaluate (7), not to the planner — it's new
    evidence about an existing paper, not a new search. Hitting
    MAX_ITERATIONS overrides all of the above and routes to verify/answer
    instead — a best-effort answer with the limitations the evaluator
    already noted is more useful than nothing at all.
    """
    if state["decision"] == "enough" or state["iteration"] >= MAX_ITERATIONS:
        return "verify"
    if state["decision"] == "need_source_context":
        return "citation"
    return "planner"


def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("intent", intent_node)
    g.add_node("planner", planner_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("evaluate", evaluator_node)
    g.add_node("decide", decision_node)
    g.add_node("citation", citation_node)
    g.add_node("verify", verify_node)
    g.add_node("answer", answer_node)

    g.set_entry_point("intent")
    g.add_conditional_edges("intent", route_after_intent)
    g.add_edge("planner", "retrieve")
    g.add_edge("retrieve", "evaluate")
    g.add_edge("evaluate", "decide")
    g.add_conditional_edges("decide", route_after_decision)
    g.add_edge("citation", "evaluate")
    g.add_edge("verify", "answer")
    g.add_edge("answer", END)

    return g.compile()
