# Research Paper Agent — Project Structure

Locked decisions this reflects: Groq (`llama-3.3-70b-versatile`) as the LLM,
LangGraph + LangChain (not hand-rolled API calls), `uv` + `pyproject.toml`
(not pip/requirements.txt), arXiv for papers + OpenAlex for citations,
FastAPI backend + React/Vite frontend as **separate top-level folders**
(no Streamlit).

Trimmed from an initial proposed tree that had real duplication — see
"Cut from the original proposal" at the bottom for what was removed and why.

## Top level

```
Agentic Rag/
├── backend/            ← Python project (uv-managed), everything below
├── frontend/            ← React + Vite, not yet scaffolded
├── docs/                 ← shared docs (not yet created)
├── architecture-diagram.html        (existing)
├── AGENTIC_RAG_ARCHITECTURE.md      (existing)
├── agentic-rag-fig1-runtime-loop.png (existing)
├── agentic-rag-fig2-ingestion.png    (existing)
├── PROJECT_STRUCTURE.md  (this file)
└── .gitignore
```

`backend/` is a self-contained `uv` project: `pyproject.toml`, `uv.lock`,
`.venv/`, `.env` all live inside it, not at the repo root. Already set up
and verified working (`uv sync` succeeded, LangGraph/LangChain/FAISS/arxiv
imports confirmed).

## backend/ — full tree, with phase each file belongs to

Phase key: **P0** = prove the control loop (5 papers, crude retrieval, real
Groq calls). **P1** = real ingestion pipeline (GROBID, chunking, FAISS/BM25,
citation graph). **P2** = full adaptive agent loop + API. **P3** = eval
benchmark. **P4** = polish/report formatting. Nothing is implemented yet —
this is the target shape, to be filled in phase by phase, not built all at
once.

```
backend/
├── pyproject.toml, uv.lock, .venv/, .env, .env.example   [done]
│
├── app/
│   ├── main.py                     FastAPI app entrypoint                    P2
│   │
│   ├── api/
│   │   ├── schemas.py              request/response Pydantic models         P2
│   │   └── routes/
│   │       ├── research.py         POST /research → runs the agent graph    P2
│   │       ├── papers.py           GET endpoints over ingested papers       P1
│   │       └── health.py           GET /health                             P0
│   │
│   ├── agent/                      the LangGraph control loop
│   │   ├── state.py                Research Workspace TypedDict (graph state) P0
│   │   ├── nodes.py                one fn per Fig.01 stage (agent/planner/…) P0
│   │   ├── decisions.py            8.1/8.2/8.3/8.4 conditional-edge routing  P0
│   │   ├── graph.py                builds + compiles the StateGraph          P0
│   │   └── memory.py               checkpointing across turns                P2
│   │
│   ├── retrieval/
│   │   ├── planner.py              stage 3→4: turns plan into retrieval calls P0
│   │   ├── semantic.py             stage 4.1 vector search                   P0
│   │   ├── bm25.py                 stage 4.2 keyword search                  P0
│   │   ├── metadata.py             stage 4.3 metadata filter                 P1
│   │   ├── citation.py             stage 6 citation-graph traversal          P1
│   │   └── fusion.py               stage 5 merge/dedupe/rank                 P0
│   │
│   ├── evaluation/
│   │   ├── evidence.py             stage 7 relevance/reliability/support     P0
│   │   ├── contradiction.py        stage 7/8.3 cross-paper conflict check    P2
│   │   ├── sufficiency.py          stage 8 enough/missing/conflict/context   P0
│   │   └── claims.py               stage 9 claim → evidence → confidence     P0
│   │
│   ├── ingestion/
│   │   ├── download.py             arXiv fetch (crude P0 → full P1)          P0/P1
│   │   ├── parser.py               GROBID structure parsing                  P1
│   │   ├── chunker.py               section-aware, 650 tok / 80 overlap      P1
│   │   ├── figures.py              caption + surrounding text only           P1
│   │   ├── tables.py               best-effort text + caption only           P1
│   │   ├── references.py           resolves refs → citation graph           P1
│   │   └── metadata.py             normalizes paper metadata                 P1
│   │
│   ├── knowledge/
│   │   ├── vector_store.py         FAISS wrapper                             P0
│   │   ├── bm25_store.py           rank_bm25 wrapper                         P0
│   │   ├── metadata_store.py       chunk/doc metadata, keyed by chunk ID     P1
│   │   └── citation_graph.py       paper→cites→paper via OpenAlex            P1
│   │
│   ├── llm/
│   │   ├── client.py               ChatGroq factory (llama-3.3-70b-versatile) P0
│   │   ├── structured.py           Pydantic-constrained LLM output helpers   P0
│   │   └── prompts.py              loads prompts/*.md                        P0
│   │
│   ├── models/                     plain domain models, used everywhere
│   │   ├── paper.py                                                          P0
│   │   ├── chunk.py                                                          P0
│   │   ├── evidence.py                                                       P0
│   │   ├── citation.py                                                       P1
│   │   └── research.py             ResearchWorkspace, ResearchReport         P0
│   │
│   └── config/
│       └── settings.py             env vars (GROQ_API_KEY, OPENALEX_EMAIL)   P0
│
├── prompts/
│   ├── research/
│   │   ├── decompose.md                                                      P0
│   │   ├── search_plan.md                                                    P0
│   │   ├── evaluate_evidence.md                                              P0
│   │   ├── detect_contradiction.md                                           P2
│   │   ├── decide_sufficiency.md                                             P0
│   │   ├── verify_claims.md                                                  P0
│   │   └── generate_report.md                                                P0
│   └── system/
│       └── research_agent.md                                                 P0
│
├── data/                           all gitignored, created at runtime
│   ├── papers/{raw,parsed,figures}/
│   ├── indexes/{vector,bm25}/
│   ├── metadata/                   (papers.db, sqlite)
│   └── citation_graph/             (graph.json)
│
├── datasets/research_questions/
│   ├── questions.json                                                        P3
│   └── expected_evidence.json                                                P3
│
├── eval/
│   ├── metrics.py                  recall@k, citation correctness, etc.      P3
│   ├── cases/
│   └── reports/
│
├── scripts/                        CLI entry points
│   ├── ingest.py                                                             P1
│   ├── build_indexes.py                                                      P1
│   ├── build_citation_graph.py                                               P1
│   └── run_eval.py                                                           P3
│
└── tests/
    ├── unit/
    │   ├── test_chunking.py                                                  P1
    │   ├── test_retrieval.py                                                 P0
    │   ├── test_citations.py                                                 P1
    │   └── test_claims.py                                                    P0
    ├── integration/
    │   ├── test_research_flow.py                                             P0
    │   └── test_agent_loop.py                                                P0
    └── fixtures/
```

## frontend/

Not yet scaffolded. React + Vite, calls the FastAPI backend over HTTP.
Framework/structure to be decided when Phase 2 (API) actually has endpoints
to call against.

## Cut from the original proposed tree, and why

- **`app/research/` (decomposer.py, researcher.py, verifier.py, claims.py,
  report.py) — dropped entirely.** Duplicated `app/agent/` (decomposition is
  stage 1, belongs in `nodes.py`) and `app/evaluation/` (verification is
  stage 9; `claims.py` existed in both folders). Not a real separate layer.
- **`docs/ARCHITECTURE.md`, `docs/AGENTIC_RAG.md` — not duplicated.**
  `AGENTIC_RAG_ARCHITECTURE.md` and `architecture-diagram.html` already exist
  at the repo root; link/move those into `docs/` instead of re-creating them.
- **`eval/run.py` — dropped, kept `scripts/run_eval.py` instead.** Same job,
  one location; all CLI entry points live in `scripts/`.
- **`app/retrieval/models.py` — dropped.** Collided with `app/models/`;
  domain models live in exactly one place.
- **`app/knowledge/indexes.py` — dropped.** Would only have been a thin
  wrapper around `vector_store.py` + `bm25_store.py`; not worth a file until
  it does real work.
- **`ui/streamlit_app.py` — dropped entirely.** Real frontend/backend split
  instead (React/Vite + FastAPI), not a Streamlit demo.

## Status

Nothing under `backend/app/`, `prompts/`, `eval/`, `scripts/`, `tests/`, or
`frontend/` has been created yet — this file is the plan, agreed but not yet
executed. `backend/pyproject.toml` + `uv.lock` + `.venv` are the only real
artifacts so far, and they're verified working.
