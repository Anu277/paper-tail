import { useEffect, useRef, useState } from "react";
import { Check, Loader2, X, AlertTriangle, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import { buildCorpus, initialStages, STAGES, type StageState } from "@/lib/corpus-stream";
import { IS_DEMO } from "@/lib/agent-stream";

function StageRow({ stage }: { stage: StageState }) {
  const meta = STAGES.find((s) => s.id === stage.id)!;
  const pct =
    stage.total && stage.total > 0
      ? Math.round(((stage.current ?? 0) / stage.total) * 100)
      : stage.status === "done"
        ? 100
        : 0;

  return (
    <li
      className={cn(
        "rounded-xl border border-transparent px-3 py-2.5 transition-colors",
        stage.status === "active" && "border-border bg-panel-raised",
      )}
    >
      <div className="flex items-center gap-3">
        <span className="grid size-4 shrink-0 place-items-center">
          {stage.status === "done" ? (
            <Check className="size-4 text-success" />
          ) : stage.status === "active" ? (
            <Loader2 className="size-3.5 animate-spin text-accent" />
          ) : (
            <span className="size-1.5 rounded-full bg-muted-foreground/50" />
          )}
        </span>
        <span
          className={cn(
            "flex-1 text-sm",
            stage.status === "pending" && "text-muted-foreground",
            stage.status === "active" && "text-foreground",
            stage.status === "done" && "text-muted-foreground",
          )}
        >
          {stage.label}
          <span className="ml-2 font-mono text-[10px] text-muted-foreground/60">
            {meta.backend}
          </span>
        </span>
        <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
          {stage.total
            ? `${(stage.current ?? 0).toLocaleString()} / ${stage.total.toLocaleString()}`
            : (stage.note ?? "")}
        </span>
      </div>

      {stage.status !== "pending" && (
        <div className="mt-2 ml-7 h-[3px] overflow-hidden rounded-full bg-border">
          {stage.total ? (
            <div
              className="h-full rounded-full bg-accent transition-[width] duration-200 ease-out"
              style={{ width: `${pct}%` }}
            />
          ) : (
            <div
              className={cn(
                "h-full rounded-full bg-accent",
                stage.status === "active" ? "w-1/3 animate-[sweep_1.4s_linear_infinite]" : "w-full",
              )}
            />
          )}
        </div>
      )}

      {stage.warning && stage.note && (
        <p className="mt-2 ml-7 flex items-center gap-1.5 text-[11px] text-accent">
          <AlertTriangle className="size-3" />
          {stage.note}
        </p>
      )}
    </li>
  );
}

export function CorpusBuilder({
  open,
  onClose,
  onBuildComplete,
}: {
  open: boolean;
  onClose: () => void;
  /** Fired once a build finishes successfully — lets the left-side corpus
   * sidebar refresh without this component knowing that sidebar exists. */
  onBuildComplete?: () => void;
}) {
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(20);
  const [running, setRunning] = useState(false);
  const [stages, setStages] = useState<StageState[]>(initialStages);
  const [summary, setSummary] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abort = useRef<(() => void) | null>(null);

  useEffect(() => () => abort.current?.(), []);

  const start = () => {
    if (!topic.trim() || running) return;
    setRunning(true);
    setSummary(null);
    setError(null);
    setStages(initialStages());
    abort.current = buildCorpus(topic.trim(), count, (event) => {
      if (event.type === "stage") {
        setStages((prev) =>
          prev.map((s) => (s.id === event.stage.id ? { ...s, ...event.stage } : s)),
        );
      } else if (event.type === "summary") {
        setSummary(event.text);
      } else if (event.type === "error") {
        setError(event.message);
        setRunning(false);
      } else {
        setRunning(false);
        onBuildComplete?.();
      }
    });
  };

  const started = running || summary !== null;

  return (
    <div
      className={cn("fixed inset-0 z-50", open ? "pointer-events-auto" : "pointer-events-none")}
      aria-hidden={!open}
    >
      <div
        onClick={onClose}
        className={cn(
          "absolute inset-0 bg-black/60 transition-opacity duration-200",
          open ? "opacity-100" : "opacity-0",
        )}
      />
      <aside
        role="dialog"
        aria-label="Add papers"
        className={cn(
          "absolute inset-y-0 right-0 flex w-full max-w-xl flex-col border-l border-border bg-panel shadow-2xl transition-transform duration-300 ease-out",
          open ? "translate-x-0" : "translate-x-full",
        )}
      >
        <header className="flex items-center gap-3 border-b border-border/70 px-6 py-4">
          <span className="grid size-8 place-items-center rounded-xl bg-panel-raised text-accent">
            <Database className="size-4" />
          </span>
          <div className="flex-1">
            <h2 className="text-sm font-semibold">Add Papers</h2>
            <p className="text-[10px] text-muted-foreground">Grow your research library</p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-panel-raised hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        </header>

        <div className="flex-1 space-y-6 overflow-y-auto px-6 py-6">
          <div className="space-y-4">
            <p className="text-xs leading-relaxed text-muted-foreground">
              Type a topic you want to read about. We'll find matching papers on arXiv, download
              them, and add them to your papers on the left so you can ask questions about them in
              chat.
            </p>
            <div className="space-y-1.5">
              <label htmlFor="topic" className="text-xs font-medium text-muted-foreground">
                What topic are you interested in?
              </label>
              <input
                id="topic"
                value={topic}
                disabled={running}
                onChange={(e) => setTopic(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && start()}
                placeholder="e.g. climate change adaptation, black holes"
                className="w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm outline-none transition-all placeholder:text-muted-foreground/60 focus:border-accent focus:ring-4 focus:ring-accent/10 disabled:opacity-60"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="count" className="text-xs font-medium text-muted-foreground">
                How many papers
              </label>
              <input
                id="count"
                type="number"
                min={1}
                max={200}
                disabled={running}
                value={count}
                onChange={(e) => setCount(Number(e.target.value) || 1)}
                className="w-32 rounded-xl border border-border bg-background px-3 py-2.5 text-sm outline-none transition-all focus:border-accent focus:ring-4 focus:ring-accent/10 disabled:opacity-60"
              />
            </div>
            <button
              onClick={start}
              disabled={running || !topic.trim()}
              className="w-full rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-accent-foreground shadow-sm transition-transform hover:scale-[1.01] disabled:opacity-40"
            >
              {running ? "Adding papers…" : "Add papers"}
            </button>
          </div>

          {started && (
            <div className="border-t border-border pt-5">
              <p className="mb-3 text-[10px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">
                Pipeline
              </p>
              <ul className="space-y-1">
                {stages.map((s) => (
                  <StageRow key={s.id} stage={s} />
                ))}
              </ul>
            </div>
          )}

          {error && (
            <p className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {error}
            </p>
          )}
        </div>

        {summary && (
          <footer className="animate-[bubble-in_260ms_ease-out] border-t border-border px-6 py-4">
            <p className="text-sm">
              <span className="text-success">Papers added.</span>{" "}
              <span className="text-muted-foreground">{summary}</span>
            </p>
            <button
              onClick={onClose}
              className="mt-3 w-full rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-accent-foreground shadow-sm transition-transform hover:scale-[1.01]"
            >
              Start chatting
            </button>
          </footer>
        )}

        {IS_DEMO && (
          <p className="border-t border-border px-6 py-2 text-[10px] text-muted-foreground">
            This is a demo pipeline. Set VITE_AGENT_API_URL to see real ingestion progress.
          </p>
        )}
      </aside>
    </div>
  );
}
