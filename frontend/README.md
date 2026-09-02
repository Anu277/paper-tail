# Insight Weaver

# Frontend UI Design — Research Paper Agent




Dark-themed, bright-orange-accented, modern/animated chat UI. Two things live

here: (1) a **Corpus Builder** to grow the paper database from the UI itself

(search arXiv, download, parse, chunk, embed, index — with live progress),

and (2) a **Chat** interface to query whatever corpus already exists, with a

collapsible **Thought Process** timeline showing the real LangGraph node

trace behind every answer, not a fake "thinking..." spinner.




Chat is the default view. Corpus Builder is reached via an explicit action,

not forced on the user every time.




---




## 1. Screen structure




```

┌─────────────────────────────────────────────┐

│  Top bar: app name · [Build Corpus] button   │

├─────────────────────────────────────────────┤

│                                               │

│   Chat message stream (scrollable)           │

│                                               │

│   ┌─ user question bubble ──────────────┐    │

│   └──────────────────────────────────────┘   │

│                                               │

│   ⌄ Thought process              (collapsed) │

│   ┌─ agent answer bubble ───────────────┐    │

│   │ ...cited final report...            │    │

│   └──────────────────────────────────────┘   │

│                                               │

├─────────────────────────────────────────────┤

│  [ Ask a question about the corpus...  ] [→] │

└─────────────────────────────────────────────┘

```




`[Build Corpus]` opens the Corpus Builder as a modal / slide-over panel, not

a full navigation away from chat — the user should never lose their

conversation to go add papers.




---




## 2. Corpus Builder (ingestion from the UI)




Two inputs, one action:




- **Topic / search query** (text field) — e.g. `"retrieval augmented generation chunking"`

- **How many papers** (number field, sane default e.g. 20)

- **Build corpus** button




On submit, the panel becomes a **live pipeline progress view** — this is a

direct UI translation of the real backend scripts (`fetch_papers` →

`parse_pdf`/GROBID → `chunk_text` → embeddings → `build_index.py` /

`build_bm25.py` / `build_citation_graph.py` / `build_metadata.py`), so every

stage shown is a stage that actually runs, in this order:




| Stage label (UI)         | Real backend step                          | Progress shown             |

|---------------------------|---------------------------------------------|-----------------------------|

| Searching arXiv            | `fetch_papers()` query                     | spinner → "N papers found"  |

| Downloading PDFs           | `fetch_papers()` PDF download loop         | `x / N` counter, per-file   |

| Parsing (GROBID)           | `parse_pdf()`                              | `x / N` counter             |

| Chunking                   | `chunk_text()` per section                 | `x / N` papers chunked      |

| Embedding                  | `HuggingFaceEmbeddings` batch encode       | `x / total_chunks` (this is the slow CPU step — show it honestly, don't hide it behind a generic spinner) |

| Building vector index      | `build_index.py` → FAISS save              | spinner → "done"            |

| Building BM25 index        | `build_bm25.py`                            | spinner → "done"            |

| Resolving citations        | `resolve_reference()` + `build_citation_graph.py` | `x / N references resolved` |

| Saving metadata            | `build_metadata.py`                        | spinner → "done"            |




Each stage is a row that goes `pending (dim) → active (orange, animated) →

done (checkmark, settles to dim)`. When it finishes, show a summary line

("23 papers, 1,140 chunks, 340 citation edges") and a **Start chatting**

button that closes the panel back to Chat.




Real constraint to surface here, not hide: OpenAlex citation resolution and

Groq calls are both rate-limited (see project memory — rolling window vs

hard daily quota). If a stage stalls on a retry/backoff, show that

honestly ("retrying, rate limited...") rather than a frozen progress bar

with no explanation.




---




## 3. Chat — the "Thought Process" trace




This is the part that has to show **real intermediate agent output**, not

placeholder text. It is a direct rendering of the actual LangGraph node

sequence for that specific run — including every loop iteration, in order,

exactly as it happened.




### 3.1 Trigger and placement




- A small pill/link, `⌄ Thought process`, sits directly above the agent's

  answer bubble for that turn.

- **While the answer is being generated**, this section is auto-expanded

  and live-updating — the "waiting for the agent" state *is* the thought

  trace filling in step by step, not a separate spinner. This requires the

  backend to stream node completions (see §5) rather than block until the

  whole graph finishes.

- Once the final answer lands, it auto-collapses to the pill; clicking it

  re-expands the full trace at any time (it's not thrown away).




### 3.2 The vertical timeline




Exactly the `o———o———o———o` shape you described — a vertical stepper, each

node execution as one dot, connected by a line, growing downward as the

run progresses:




```

 ⌄ Thought process




   ○ Planner

   │  query: "chunking strategies RAG academic texts"

   │  methods: semantic, bm25

   │

   ○ Retrieve

   │  11 candidates → 11 unseen → 4 kept

   │

   ○ Evaluate

   │  4 claims extracted, 0 contradictions, 1 gap noted

   │

   ◆ Decide  →  need_source_context (2607.01852)

   │  "claims cover refs [2]-[5], but broader related

   │   work beyond these four may exist"

   │

   ○ Citation traversal

   │  2607.01852 cites → 3 citations surfaced

   │

   ── Iteration 2 ──

   │

   ○ Evaluate

   │  claims now cover related work comprehensively

   │

   ◆ Decide  →  enough

   │

   ○ Verify

   │  4 / 4 claims confirmed against evidence

   │

   ● Answer

      final report generated

```




Visual rules:

- `○` = normal completed step. `◆` = a decision node (diamond, since it's a

  branch point — visually distinct because it's the one that changes what

  happens next). `●` = terminal step (Answer), filled solid.

- The **currently running** step pulses with a soft orange glow (animated,

  looping opacity, not spinning) until it completes, then settles to solid.

- Each step's caption is the *real* short summary already being printed

  server-side today (`[planner] query: ...`, `[decision] ... target=...`,

`[citation] ... citation(s) surfaced`) — reuse that exact text, don't

  invent new copy for it.

- Iterations are visually grouped with a thin labeled divider (`── Iteration 2 ──`)

  so a 3-loop run doesn't read as one flat undifferentiated list.

- Steps animate in one at a time (fade + slight upward slide, ~150ms) as

  they arrive — this is what makes waiting feel alive instead of frozen.




### 3.3 Node → UI content mapping




| Node (`app/agent/nodes.py`) | Marker | Caption content |

|---|---|---|

| `planner_node` | ○ | query text, chosen methods, year range if set |

| `retrieve_node` | ○ | candidate count → unseen → kept (dedupe/filter stats) |

| `evaluator_node` | ○ | claim count, contradiction count, missing-evidence notes |

| `decision_node` | ◆ | decision value + one-line reasoning + target_paper_id if citation path |

| `citation_node` | ○ (only appears if triggered) | which paper, how many citations surfaced |

| `verify_node` | ○ | claims confirmed vs dropped |

| `answer_node` | ● | (no separate caption — this step's "content" is the answer bubble itself) |




### 3.4 Final answer bubble




Below the (collapsed-by-default, once done) trace: the actual chat bubble,

markdown-rendered, with `[paper_id]` citation tags styled as small

orange-outlined pill badges — clicking one could later jump to that paper's

entry in a sources panel (not required for v1, just don't design against it).




---




## 4. Visual language




**Theme: dark background, bright orange accent.** Tokens (adjust exact

hexes during implementation, but keep this contrast relationship):




| Token | Value (approx) | Use |

|---|---|---|

| `--bg` | `#0c0c0e` | page background |

| `--panel` | `#17171b` | chat bubbles, cards, modal |

| `--panel-raised` | `#1f1f24` | hovered/active rows |

| `--border` | `#2a2a30` | hairlines, dividers |

| `--text` | `#eceae6` | primary text |

| `--text-dim` | `#8b8b93` | captions, pending steps |

| `--accent` | `#ff6a1a` | primary orange — buttons, active glow, decision diamonds |

| `--accent-dim` | `#ff6a1a` at 25% opacity | glow rings, subtle highlights |

| `--success` | `#3ecf8e` | completed checkmarks (sparingly — orange stays the hero color) |




**Motion**, kept purposeful, not decorative:

- Stepper nodes: fade+slide-in on arrival, pulse-glow while active.

- Thought-process expand/collapse: height auto-animate (~200ms ease-out), not an instant snap.

- Corpus Builder stage rows: left-to-right progress-bar fill in `--accent`, checkmark morphs in on completion.

- Chat message entry: new bubbles slide up + fade in.

- Avoid gratuitous motion elsewhere (no bouncing, no infinite background animations) — the animation budget goes toward *making the agent's real work visible*, that's the actual design goal here, not decoration for its own sake.




**Typography**: a modern geometric/grotesk sans (e.g. Inter, or similar) —

clean, high-legibility at small caption sizes since a lot of this UI is

dense status text.




---




## 5. Backend implication (prerequisite, not yet built)




Today, `POST /research` (`app/api/routes/research.py`) calls

`graph.invoke(initial_state)` — one blocking call that returns only after

the *entire* loop finishes. That cannot power the live-updating trace in

§3.2: there is nothing to stream yet.




To make the "steps appear one at a time as they happen" behavior real

(not faked with client-side setTimeout delays, which would violate the

project's whole "show real reasoning" premise), the backend needs to swap

to LangGraph's streaming interface — `graph.stream(initial_state)`, which

yields the state delta after each node completes — pushed to the frontend

over Server-Sent Events or a WebSocket instead of a single JSON response.

This is real backend work, not just a frontend concern, and should be

scoped before frontend implementation starts on the chat view.




The Corpus Builder's live progress (§2) has the same requirement: the

ingestion scripts currently just `print()` to a terminal — turning that

into UI progress needs the same kind of streaming channel (or simpler:

periodic progress writes to a state file/endpoint the frontend polls, if

full streaming is more than wanted for v1 of the builder specifically).




---




## 6. Explicitly out of scope for v1




- Editing/deleting individual papers from the corpus via the UI

- Multi-corpus / multi-project switching

- Clicking a `[paper_id]` citation to open a full sources/reference panel

  (design doesn't block it, just not built now)

- Auth / multi-user (single local user assumed)

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/6e651170-e6fc-45c6-85bc-e6bcd15371ce).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
