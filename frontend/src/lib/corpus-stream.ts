/**
 * Corpus ingestion progress channel.
 *
 * Mirrors the real pipeline (fetch_papers → parse_pdf/GROBID → chunk_text →
 * embeddings → build_index.py → build_bm25.py → build_citation_graph.py →
 * build_metadata.py). Progress is streamed from the backend when
 * VITE_AGENT_API_URL is set; otherwise a labelled demo run drives the UI.
 */

import { AGENT_API_URL } from "./agent-stream";

export type StageId =
  | "search"
  | "download"
  | "parse"
  | "chunk"
  | "embed"
  | "index"
  | "bm25"
  | "citations"
  | "metadata";

export type StageState = {
  id: StageId;
  label: string;
  status: "pending" | "active" | "done";
  /** Free-form status line, e.g. "N papers found" or "retrying, rate limited…". */
  note?: string;
  current?: number;
  total?: number;
  warning?: boolean;
};

export type CorpusEvent =
  | { type: "stage"; stage: Partial<StageState> & { id: StageId } }
  | { type: "summary"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

export const STAGES: Array<{ id: StageId; label: string; backend: string }> = [
  { id: "search", label: "Searching arXiv", backend: "fetch_papers()" },
  { id: "download", label: "Downloading PDFs", backend: "fetch_papers()" },
  { id: "parse", label: "Parsing (GROBID)", backend: "parse_pdf()" },
  { id: "chunk", label: "Chunking", backend: "chunk_text()" },
  { id: "embed", label: "Embedding", backend: "HuggingFaceEmbeddings" },
  { id: "index", label: "Building vector index", backend: "build_index.py" },
  { id: "bm25", label: "Building BM25 index", backend: "build_bm25.py" },
  {
    id: "citations",
    label: "Resolving citations",
    backend: "build_citation_graph.py",
  },
  { id: "metadata", label: "Saving metadata", backend: "build_metadata.py" },
];

export function initialStages(): StageState[] {
  return STAGES.map((s) => ({ id: s.id, label: s.label, status: "pending" }));
}

type Handler = (event: CorpusEvent) => void;

export function buildCorpus(
  topic: string,
  count: number,
  onEvent: Handler,
): () => void {
  if (!AGENT_API_URL) return demoBuild(count, onEvent);

  const controller = new AbortController();
  void (async () => {
    try {
      const res = await fetch(`${AGENT_API_URL}/corpus/build/stream`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ topic, count }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error(`Ingest returned ${res.status}`);
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
          if (data) onEvent(JSON.parse(data) as CorpusEvent);
        }
      }
      onEvent({ type: "done" });
    } catch (err) {
      if (controller.signal.aborted) return;
      onEvent({
        type: "error",
        message: err instanceof Error ? err.message : "Ingestion failed",
      });
    }
  })();
  return () => controller.abort();
}

/* ---------------------------------- demo --------------------------------- */

function demoBuild(count: number, onEvent: Handler): () => void {
  let cancelled = false;
  const timers: Array<ReturnType<typeof setTimeout>> = [];
  const sleep = (ms: number) =>
    new Promise<void>((resolve) => timers.push(setTimeout(resolve, ms)));

  const chunks = count * 48;

  void (async () => {
    const counted = async (
      id: StageId,
      total: number,
      stepMs: number,
      stride = 1,
      mid?: { at: number; note: string },
    ) => {
      onEvent({ type: "stage", stage: { id, status: "active", total } });
      for (let i = stride; i <= total; i += stride) {
        await sleep(stepMs);
        if (cancelled) return;
        const current = Math.min(i, total);
        const throttled = Boolean(
          mid && current >= mid.at && current < mid.at + stride * 3,
        );
        onEvent({
          type: "stage",
          stage: {
            id,
            status: "active",
            current,
            total,
            note: throttled && mid ? mid.note : "",
            warning: throttled,
          },
        });

      }
      onEvent({
        type: "stage",
        stage: { id, status: "done", current: total, total, warning: false },
      });
    };

    const spinner = async (id: StageId, ms: number, note: string) => {
      onEvent({ type: "stage", stage: { id, status: "active" } });
      await sleep(ms);
      if (cancelled) return;
      onEvent({ type: "stage", stage: { id, status: "done", note } });
    };

    await spinner("search", 1200, `${count} papers found`);
    if (cancelled) return;
    await counted("download", count, 130);
    if (cancelled) return;
    await counted("parse", count, 190);
    if (cancelled) return;
    await counted("chunk", count, 110);
    if (cancelled) return;
    await counted("embed", chunks, 45, Math.max(1, Math.round(chunks / 40)));
    if (cancelled) return;
    await spinner("index", 1000, "done");
    if (cancelled) return;
    await spinner("bm25", 700, "done");
    if (cancelled) return;
    await counted("citations", count * 15, 40, 9, {
      at: Math.round(count * 6),
      note: "retrying, rate limited by OpenAlex…",
    });
    if (cancelled) return;
    await spinner("metadata", 600, "done");
    if (cancelled) return;
    onEvent({
      type: "summary",
      text: `${count} papers, ${chunks.toLocaleString()} chunks, ${(count * 15).toLocaleString()} citation edges`,
    });
    onEvent({ type: "done" });
  })();

  return () => {
    cancelled = true;
    timers.forEach(clearTimeout);
  };
}
