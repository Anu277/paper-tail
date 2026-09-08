"""Runs the golden dataset through the real compiled agent graph and scores
retrieval/citation accuracy mechanically against expected_paper_ids — no
fuzzy text grading, just: did the final claims cite the right paper(s), and
did it avoid citing wrong ones.

Run: uv run python -m eval.run_eval
"""

import json
import time
from pathlib import Path

from app.agent.graph import build_graph
from eval.golden_set import GOLDEN_SET

REPORT_PATH = Path(__file__).parent / "reports" / "latest.json"


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


def score_case(case: dict, final_state: dict) -> dict:
    expected = set(case["expected_paper_ids"])
    cited = set(final_state["claims_by_paper"].keys())

    true_positives = expected & cited
    false_negatives = expected - cited  # expected but never cited — a miss
    false_positives = cited - expected  # cited but not expected — possibly wrong

    if expected:
        precision = len(true_positives) / len(cited) if cited else 0.0
        recall = len(true_positives) / len(expected)
    else:
        # Adversarial cases (e.g. g11): nothing SHOULD be cited. Citing
        # nothing is a perfect score; citing anything is a real failure
        # (a fabricated answer dressed up with a real paper_id), not a
        # partial-credit situation the normal formula would represent
        # honestly (it would divide by zero or silently read as 0.0).
        precision = 1.0 if not cited else 0.0
        recall = 1.0

    report_lower = final_state["final_report"].lower()
    expected_facts = case["expected_facts"]
    facts_found = [f for f in expected_facts if f.lower() in report_lower]
    facts_missing = [f for f in expected_facts if f.lower() not in report_lower]
    fact_coverage = len(facts_found) / len(expected_facts) if expected_facts else None

    # Evidence.source == "citation" is the one reliable signal that
    # citation_node actually ran at some point in this run — target_paper_id
    # in final_state only reflects the LAST decision, so a run that used
    # citation traversal mid-loop but then answered "enough" would look
    # like it never happened if we checked that field instead.
    citation_fired = any(e.get("source") == "citation" for e in final_state["evidence"])

    return {
        "id": case["id"],
        "question": case["question"],
        "expected_paper_ids": sorted(expected),
        "cited_paper_ids": sorted(cited),
        "true_positives": sorted(true_positives),
        "false_negatives": sorted(false_negatives),
        "false_positives": sorted(false_positives),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "facts_found": facts_found,
        "facts_missing": facts_missing,
        "fact_coverage": round(fact_coverage, 3) if fact_coverage is not None else None,
        "expects_citation": case["expects_citation"],
        "citation_fired": citation_fired,
        "citation_check_ok": citation_fired == case["expects_citation"]
        if case["expects_citation"]
        else True,  # expects_citation=False is a soft hint, not a hard fail if it fires anyway
        "iterations": final_state["iteration"],
        "decision": final_state["decision"],
        "final_report": final_state["final_report"],
    }


def summarize(results: list[dict]) -> dict:
    fact_scores = [r["fact_coverage"] for r in results if r["fact_coverage"] is not None]
    return {
        "n_cases": len(results),
        "avg_precision": round(sum(r["precision"] for r in results) / len(results), 3),
        "avg_recall": round(sum(r["recall"] for r in results) / len(results), 3),
        "avg_fact_coverage": round(sum(fact_scores) / len(fact_scores), 3) if fact_scores else None,
        "citation_checks_passed": f"{sum(1 for r in results if r['citation_check_ok'])}/{len(results)}",
        "avg_iterations": round(sum(r["iterations"] for r in results) / len(results), 2),
        "total_elapsed_seconds": round(sum(r["elapsed_seconds"] for r in results), 1),
    }


def _save_report(results: list[dict], stopped_early: bool, error: str | None = None) -> None:
    # Written after EVERY case, not just at the end — a case N+1 crash (a
    # real Groq daily-token-quota 429 killed a run mid-way once) must not
    # lose the N cases that already completed and were already paid for.
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summarize(results) if results else None,
        "results": results,
        "stopped_early": stopped_early,
    }
    if error:
        payload["error"] = error
    REPORT_PATH.write_text(json.dumps(payload, indent=2))


def main() -> None:
    graph = build_graph()
    results = []

    for i, case in enumerate(GOLDEN_SET, start=1):
        print(f"[{i}/{len(GOLDEN_SET)}] {case['id']}: {case['question'][:70]!r}")
        start = time.monotonic()
        try:
            final_state = graph.invoke(_initial_state(case["question"]))
        except Exception as e:  # noqa: BLE001 — must save what's already completed before propagating
            elapsed = time.monotonic() - start
            print(f"  FAILED after {elapsed:.1f}s: {e}")
            _save_report(results, stopped_early=True, error=str(e))
            print(f"\n{len(results)}/{len(GOLDEN_SET)} cases completed and saved to {REPORT_PATH} before the failure.")
            raise
        elapsed = time.monotonic() - start
        result = score_case(case, final_state)
        result["elapsed_seconds"] = round(elapsed, 1)
        results.append(result)
        print(
            f"  precision={result['precision']} recall={result['recall']} "
            f"fact_coverage={result['fact_coverage']} "
            f"iterations={result['iterations']} ({elapsed:.1f}s)"
        )
        if result["false_negatives"]:
            print(f"  MISSED expected paper(s): {result['false_negatives']}")
        if result["false_positives"]:
            print(f"  UNEXPECTED paper(s) cited: {result['false_positives']}")
        if result["facts_missing"]:
            print(f"  MISSED expected fact(s): {result['facts_missing']}")
        if not result["citation_check_ok"]:
            print(
                f"  CITATION CHECK FAILED: expected_citation={result['expects_citation']} "
                f"actual={result['citation_fired']}"
            )
        _save_report(results, stopped_early=False)

    print("\n=== SUMMARY ===")
    for k, v in summarize(results).items():
        print(f"{k}: {v}")
    print(f"\nFull report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
