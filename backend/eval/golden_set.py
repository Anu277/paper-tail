"""Golden dataset: real questions against the actual 6-paper corpus, with
expected_paper_ids verified by hand from real agent runs earlier in this
project (not guessed) — e.g. question 1's TACRED claim, question 4's three
chunking strategies, and question 6's four QA datasets were all confirmed
live against the real papers before being written here.

Each case:
- question
- expected_paper_ids: which paper_id(s) a correct answer MUST cite
- expected_facts: substrings (case-insensitive) that MUST appear somewhere
  in final_report for the answer to count as factually complete — not just
  "cited the right paper" but "actually said the right thing"
- expects_citation: whether this question genuinely needs citation
  traversal to answer well (scored against Evidence.source == "citation"
  showing up anywhere in the run's accumulated evidence — the real signal
  for "did citation traversal actually fire", since target_paper_id in
  final_state only reflects the LAST decision, not the whole run)
- notes: free text for a human reviewer, not scored
"""

GOLDEN_SET = [
    {
        "id": "g1",
        "question": "What dataset is used to evaluate ETRAG's relation extraction performance?",
        "expected_paper_ids": ["2406.03790"],
        "expected_facts": ["TACRED"],
        "expects_citation": False,
        "notes": "Direct fact lookup, single paper.",
    },
    {
        "id": "g2",
        "question": "What metrics does the semantic alignment RAG method use for evaluation?",
        "expected_paper_ids": ["2603.04647"],
        "expected_facts": ["EM", "F1", "BLEU", "ROUGE-L"],
        "expects_citation": False,
        "notes": "Four named metrics, all should appear.",
    },
    {
        "id": "g3",
        "question": "What metrics does the RAG noise robustness benchmark use?",
        "expected_paper_ids": ["2309.01431"],
        "expected_facts": ["Accuracy", "Rejection"],
        "expects_citation": False,
        "notes": "Accuracy, rejection rate, error detection/correction rate.",
    },
    {
        "id": "g4",
        "question": "What chunking strategies does the paper on academic text chunking evaluate?",
        "expected_paper_ids": ["2607.01852"],
        "expected_facts": ["fixed", "recursive", "semantic"],
        "expects_citation": False,
        "notes": "fixed-sized, format-based recursive, cluster-based semantic.",
    },
    {
        "id": "g5",
        "question": "What evaluation framework is used to assess chunking strategies for RAG?",
        "expected_paper_ids": ["2607.01852"],
        "expected_facts": ["RAGAs", "faithfulness"],
        "expects_citation": True,
        "notes": "RAGAs framework — faithfulness, answer relevancy, AQS. Live run "
        "already showed this firing citation traversal 3x chasing detail.",
    },
    {
        "id": "g6",
        "question": "What datasets is the multi layered thoughts RAG method (METRAG) evaluated on?",
        "expected_paper_ids": ["2405.19893"],
        "expected_facts": ["PopQA"],
        "expects_citation": True,
        "notes": "NQ, TriviaQA, HotpotQA, PopQA — live run only ever confirmed "
        "PopQA directly from evidence, chased the rest via citation traversal.",
    },
    {
        "id": "g7",
        "question": "Which paper addresses the non-differentiability problem in retrieval-augmented generation for relation extraction?",
        "expected_paper_ids": ["2406.03790"],
        "expected_facts": ["differentiab"],
        "expects_citation": False,
        "notes": "ETRAG's core motivation. Live run needed a replan (iteration 2) to find it.",
    },
    {
        "id": "g8",
        "question": "What prior work does the chunking strategies paper cite for its cluster-based chunking method?",
        "expected_paper_ids": ["2607.01852"],
        "expected_facts": ["Qu"],
        "expects_citation": True,
        "notes": "Tests citation traversal directly — should surface Qu et al.",
    },
    {
        "id": "g9",
        "question": "Compare the evaluation metrics used across the RAG papers in this corpus.",
        "expected_paper_ids": ["2603.04647", "2309.01431", "2405.19893", "2607.01852"],
        "expected_facts": [],
        "expects_citation": False,
        "notes": "Multi-paper synthesis — hardest case. Live run scored recall=0.5, "
        "only found 2 of 4 expected papers and hit the iteration cap.",
    },
    {
        "id": "g10",
        "question": "What topic does 2306.14753 cover?",
        "expected_paper_ids": ["2306.14753"],
        "expected_facts": ["polynomial", "chaos"],
        "expects_citation": False,
        "notes": "Honesty check — this paper is actually about polynomial chaos neural "
        "networks, not graph neural networks, despite being the top hit for a "
        "'graph neural networks' search. Answer should not fabricate a GNN topic.",
    },
    {
        "id": "g11",
        "question": "What accuracy score does 2306.14753 report for graph neural network node classification?",
        "expected_paper_ids": [],
        "expected_facts": [],
        "expects_citation": False,
        "notes": "Adversarial/verification stress test: 2306.14753 is NOT about GNNs "
        "at all, so there is no real answer to this question. A well-behaved run "
        "should have evaluator_node note this as missing/ungrounded, and if it "
        "ever DID hallucinate a number, verify_node should catch and drop it. "
        "expected_paper_ids is deliberately empty — citing ANY paper with a "
        "fabricated accuracy figure here is a real failure, not a partial credit.",
    },
]
