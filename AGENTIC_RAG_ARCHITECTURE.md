# Agentic RAG Architecture

This diagram separates the **runtime research loop** from the **offline knowledge-ingestion pipeline**. The research agent owns planning and decisions; retrieval, evaluation, and answer writing are tools/services it calls.

## 1. Runtime: research and answer loop

```text
                                  ┌──────────────────────┐
                                  │         USER         │
                                  │ question + context   │
                                  └──────────┬───────────┘
                                             │
                                             ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                        RESEARCH AGENT / ORCHESTRATOR                       │
│                                                                           │
│  • understands and decomposes the question                                │
│  • makes a research plan and chooses the next tool/action                 │
│  • selects retrieval strategy and stopping criteria                       │
│  • updates state; it does not treat RAG as the decision-maker             │
└───────┬───────────────────────────────┬───────────────────────────┬───────┘
        │                               │                           │
        │ create / revise query         │ inspect evidence state    │ answer when ready
        ▼                               ▼                           ▼
┌───────────────────────┐      ┌───────────────────────┐   ┌──────────────────────┐
│ QUERY & SEARCH PLANNER│      │    RESEARCH STATE     │   │  ANSWER COMPOSER     │
│                       │      │                       │   │                      │
│ • sub-questions       │      │ • plan / search log   │   │ • grounded response  │
│ • queries             │      │ • claims + evidence   │   │ • inline citations   │
│ • filters             │      │ • gaps/conflicts      │   │ • uncertainty        │
│ • retrieval settings  │      │ • source provenance   │   │ • no unsupported     │
│ • reference traversal │      │ • retrieved chunks    │   │   claims              │
└───────────┬───────────┘      └───────────▲───────────┘   └──────────┬───────────┘
            │                              │               └──────────┬───────────┘
            │ retrieval request             │ evaluated evidence         │ draft
            ▼                              │                            ▼
┌───────────────────────────────────────────┴─────────────────────────────────┐
│                            RETRIEVAL TOOLS (RAG)                             │
│                                                                              │
│                         ┌─────────────────────┐                              │
│                         │ RETRIEVAL ROUTER    │                              │
│                         │ applies agent plan  │                              │
│                         └──────────┬──────────┘                              │
│                   ┌────────────────┼────────────────┐                        │
│                   ▼                ▼                ▼                        │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐  │
│  │ Vector retrieval │    │ BM25 / keyword   │    │ Metadata filter      │  │
│  │ semantic matches │    │ exact terms      │    │ source/date/type/etc │  │
│  └────────┬─────────┘    └────────┬─────────┘    └──────────┬───────────┘  │
│           │                       │                           │              │
│           └──────────────┬────────┴──────────────┬────────────┘              │
│                          ▼                       ▼                           │
│                   ┌─────────────────────────────────────┐                    │
│                   │ HYBRID FUSION + RERANKING            │                    │
│                   │ score, deduplicate, diversify results│                    │
│                   └──────────────────┬──────────────────┘                    │
│                                      ▼                                       │
│                   ┌─────────────────────────────────────┐                    │
│                   │ EVIDENCE PACKET                     │                    │
│                   │ chunk text + score + source +        │                    │
│                   │ document ID + location + metadata    │                    │
│                   └──────────────────┬──────────────────┘                    │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       │
                                       ▼
                         ┌─────────────────────────────┐
                         │ EVIDENCE / CLAIM EVALUATOR  │
                         │                             │
                         │ • relevance and quality     │
                         │ • entailment / claim support│
                         │ • source reliability        │
                         │ • conflicts and missing data│
                         │ • citation coverage         │
                         └──────────────┬──────────────┘
                                        │
                                        │ update state + recommendation
                                        └──────────────────────────────┐
                                                                       │
                                                                       ▼
                                                     ┌─────────────────────────┐
                                                     │ AGENT NEXT DECISION     │
                                                     │                         │
                                                     │ enough and verified?    │
                                                     └──────┬──────────┬───────┘
                                                            │ yes      │ no
                                                            ▼          ▼
                                                   ┌──────────────┐  revise query,
                                                   │ FINAL ANSWER │  filters, source,
                                                   │ + CITATIONS  │  or strategy
                                                   └──────┬───────┘       │
                                                          │               │
                                                          ▼               │
                                                        USER ◄────────────┘
```

The `AGENT NEXT DECISION` is a decision made by the same Research Agent at the top; it is shown again only to make the loop readable. It is **not** a separate autonomous component.

## 2. Offline: knowledge ingestion and indexing

```text
┌───────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE SOURCES                             │
│ PDFs | office documents | web pages | databases | approved APIs       │
└──────────────────────────────────┬────────────────────────────────────┘
                                   │ collect / sync
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ ACQUISITION + VERSIONING                                               │
│ source URI, permissions, document ID, fetch time, checksum/version     │
└──────────────────────────────────┬────────────────────────────────────┘
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PARSE / OCR / CLEAN / NORMALIZE                                        │
│ text, structure, tables where supported, language, canonical metadata  │
└──────────────────────────────────┬────────────────────────────────────┘
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ CHUNK + ENRICH                                                         │
│ chunk IDs; headings; page/section offsets; source and access metadata  │
└──────────────────────────────────┬────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
      ┌──────────────────────────┐  ┌──────────────────────────┐
      │ EMBEDDING / VECTOR INDEX │  │ SPARSE / BM25 INDEX       │
      │ vectors keyed by chunk ID│  │ terms keyed by chunk ID   │
      └────────────┬─────────────┘  └────────────┬─────────────┘
                   │                             │
                   └──────────────┬──────────────┘
                                  ▼
                  ┌─────────────────────────────────┐
                  │ DOCUMENT + METADATA STORE        │
                  │ original docs, chunks, locations,│
                  │ links, ACLs, versions, provenance│
                  └─────────────────────────────────┘
```

At runtime, the RAG tools query the vector and BM25 indexes, then use the document/metadata store to return the exact chunk, its source location, and citation metadata.

## Corrections from `chatgpt`

| Change | Why |
|---|---|
| Added explicit **Research State** | The agent needs persistent plan, search history, claims, gaps, and provenance to make an informed next decision. |
| Moved “Agent Decision” back inside the Research Agent conceptually | The original says the agent is the controller, then diagrams a second decision component; this can imply two controllers. |
| Made metadata filtering a peer retrieval control, rather than a mandatory stage after vector/BM25 search | Filters can be applied before, during, or after retrieval depending on the search engine and query. |
| Added a distinct hybrid fusion/reranking stage | Vector and BM25 result lists must be combined and ordered; simply joining them does not produce good retrieval. |
| Added an evidence packet with document IDs, locations, and provenance | Citations require traceable source locations, not just “retrieved documents/chunks.” |
| Added answer composition and citation/claim validation | “Enough evidence” should still produce a grounded, cited response and prevent unsupported claims. |
| Corrected the ingestion data flow | Vector and BM25 indexes are separate indexes keyed by chunk ID; they should not flow into a single metadata store as if it stores the indexes. |
| Added acquisition, versioning, parsing/OCR, and access metadata | These make a production knowledge base reproducible, updatable, and permission-safe. |
| Kept the retrieval/evaluation loop | This was the original diagram’s strongest and correct central idea: RAG retrieves; the agent decides whether and how to retrieve again. |

## Scope note

This is a strong general architecture. If the system must search the live web or APIs, model those as additional agent tools with their own fetch, permission, and citation path; do not silently treat live results as already indexed corpus data.
