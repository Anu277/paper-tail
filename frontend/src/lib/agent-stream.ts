/**
 * Streaming contract for the research agent.
 *
 * The UI is built against a Server-Sent Events channel that emits one event per
 * completed LangGraph node (`graph.stream(initial_state)` server-side).
 * Point VITE_AGENT_API_URL at that backend and the real trace renders as-is.
 *
 * When no backend is configured the client falls back to a clearly-labelled
 * DEMO run so the interface can be reviewed. The demo is never used when a
 * backend URL is present.
 */

export type NodeKind =
  | "intent"
  | "planner"
  | "retrieve"
  | "evaluator"
  | "decision"
  | "citation"
  | "verify"
  | "answer";

export type TraceStep = {
  id: string;
  node: NodeKind;
  label: string;
  iteration: number;
  /** Exact short summary printed server-side, e.g. `[planner] query: ...`. */
  caption?: string;
  detail?: string;
  status: "active" | "done";
};

export type AgentEvent =
  | { type: "step"; step: Omit<TraceStep, "status"> }
  | { type: "answer"; markdown: string }
  | { type: "error"; message: string }
  | { type: "done" };

export const NODE_LABELS: Record<NodeKind, string> = {
  intent: "Understanding message",
  planner: "Planner",
  retrieve: "Retrieve",
  evaluator: "Evaluate",
  decision: "Decide",
  citation: "Citation traversal",
  verify: "Verify",
  answer: "Answer",
};

export const AGENT_API_URL: string | undefined = (
  import.meta.env as Record<string, string | undefined>
)["VITE_AGENT_API_URL"];

export const IS_DEMO = !AGENT_API_URL;

type Handler = (event: AgentEvent) => void;

/** Streams a research run. Returns an abort function. */
export function runResearch(question: string, onEvent: Handler): () => void {
  if (!AGENT_API_URL) return runDemo(question, onEvent);

  const controller = new AbortController();
  void (async () => {
    try {
      const res = await fetch(`${AGENT_API_URL}/research/stream`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error(`Agent returned ${res.status}`);

      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += value;
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const data = frame
            .split("\n")
            .filter((l) => l.startsWith("data:"))
            .map((l) => l.slice(5).trim())
            .join("");
          if (!data) continue;
          onEvent(JSON.parse(data) as AgentEvent);
        }
      }
      onEvent({ type: "done" });
    } catch (err) {
      if (controller.signal.aborted) return;
      onEvent({
        type: "error",
        message: err instanceof Error ? err.message : "Agent stream failed",
      });
    }
  })();

  return () => controller.abort();
}

/* ---------------------------------- demo --------------------------------- */

function runDemo(question: string, onEvent: Handler): () => void {
  const short = question.length > 52 ? `${question.slice(0, 52)}…` : question;
  const script: Array<{ wait: number; event: AgentEvent }> = [
    {
      wait: 500,
      event: {
        type: "step",
        step: {
          id: "s1",
          node: "planner",
          label: NODE_LABELS.planner,
          iteration: 1,
          caption: `query: "${short}"`,
          detail: "methods: semantic, bm25",
        },
      },
    },
    {
      wait: 900,
      event: {
        type: "step",
        step: {
          id: "s2",
          node: "retrieve",
          label: NODE_LABELS.retrieve,
          iteration: 1,
          caption: "11 candidates → 11 unseen → 4 kept",
        },
      },
    },
    {
      wait: 1100,
      event: {
        type: "step",
        step: {
          id: "s3",
          node: "evaluator",
          label: NODE_LABELS.evaluator,
          iteration: 1,
          caption: "4 claims extracted, 0 contradictions, 1 gap noted",
        },
      },
    },
    {
      wait: 800,
      event: {
        type: "step",
        step: {
          id: "s4",
          node: "decision",
          label: NODE_LABELS.decision,
          iteration: 1,
          caption: "need_source_context → 2607.01852",
          detail:
            '"claims cover refs [2]-[5], but broader related work beyond these four may exist"',
        },
      },
    },
    {
      wait: 1000,
      event: {
        type: "step",
        step: {
          id: "s5",
          node: "citation",
          label: NODE_LABELS.citation,
          iteration: 1,
          caption: "2607.01852 cites → 3 citations surfaced",
        },
      },
    },
    {
      wait: 1200,
      event: {
        type: "step",
        step: {
          id: "s6",
          node: "evaluator",
          label: NODE_LABELS.evaluator,
          iteration: 2,
          caption: "claims now cover related work comprehensively",
        },
      },
    },
    {
      wait: 700,
      event: {
        type: "step",
        step: {
          id: "s7",
          node: "decision",
          label: NODE_LABELS.decision,
          iteration: 2,
          caption: "enough",
        },
      },
    },
    {
      wait: 900,
      event: {
        type: "step",
        step: {
          id: "s8",
          node: "verify",
          label: NODE_LABELS.verify,
          iteration: 2,
          caption: "4 / 4 claims confirmed against evidence",
        },
      },
    },
    {
      wait: 800,
      event: {
        type: "step",
        step: {
          id: "s9",
          node: "answer",
          label: NODE_LABELS.answer,
          iteration: 2,
          caption: "final report generated",
        },
      },
    },
    {
      wait: 400,
      event: {
        type: "answer",
        markdown: `**Demo answer** — no agent backend is connected, so this is placeholder prose rendered through the real answer pipeline.

Chunking strategy dominates retrieval quality on academic text. Section-aware splitting keeps method and result statements intact [2607.01852], while fixed 512-token windows fragment them [2604.10021]. Hybrid dense + BM25 retrieval recovers most of the loss from naive chunking [2512.00931], and citation traversal adds related work that lexical search misses [2607.01852].

Set \`VITE_AGENT_API_URL\` to stream a real run.`,
      },
    },
    { wait: 100, event: { type: "done" } },
  ];

  let cancelled = false;
  let timer: ReturnType<typeof setTimeout>;
  let i = 0;
  const tick = () => {
    if (cancelled || i >= script.length) return;
    const { wait, event } = script[i++]!;
    timer = setTimeout(() => {
      if (cancelled) return;
      onEvent(event);
      tick();
    }, wait);
  };
  tick();

  return () => {
    cancelled = true;
    clearTimeout(timer);
  };
}
