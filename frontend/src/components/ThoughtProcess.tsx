import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TraceStep } from "@/lib/agent-stream";

function Marker({ step }: { step: TraceStep }) {
  const active = step.status === "active";
  const isDecision = step.node === "decision";
  const isTerminal = step.node === "answer";

  return (
    <span
      className={cn(
        "relative z-10 mt-1 grid size-3 shrink-0 place-items-center",
        active && "glow-active rounded-full",
      )}
      aria-hidden
    >
      <span
        className={cn(
          "block size-3 border-2 transition-colors",
          isDecision ? "rotate-45 rounded-[2px]" : "rounded-full",
          isTerminal || isDecision
            ? "border-accent bg-accent"
            : active
              ? "border-accent bg-background"
              : "border-muted-foreground bg-background",
          isDecision && !active && "border-accent bg-accent",
        )}
      />
    </span>
  );
}

export function ThoughtProcess({ steps, running }: { steps: TraceStep[]; running: boolean }) {
  const [open, setOpen] = useState(running);
  const [height, setHeight] = useState<number | undefined>(undefined);
  const inner = useRef<HTMLDivElement>(null);
  const wasRunning = useRef(running);

  useEffect(() => {
    if (running) setOpen(true);
    if (wasRunning.current && !running) setOpen(false);
    wasRunning.current = running;
  }, [running]);

  useEffect(() => {
    if (!inner.current) return;
    setHeight(open ? inner.current.scrollHeight : 0);
  }, [open, steps]);

  if (steps.length === 0) return null;

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="group inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5 text-xs text-muted-foreground shadow-sm transition-colors hover:bg-panel-raised hover:text-foreground"
        aria-expanded={open}
      >
        <ChevronDown
          className={cn("size-3.5 transition-transform duration-200", open && "rotate-180")}
        />
        Thought process
        <span className="text-[10px] text-muted-foreground/70">{steps.length} steps</span>
      </button>

      <div
        style={{ height: height === undefined ? undefined : `${height}px` }}
        className="overflow-hidden transition-[height] duration-200 ease-out"
      >
        <div
          ref={inner}
          className="ml-1 mt-3 rounded-2xl border border-border/70 bg-background/60 p-3"
        >
          <ol className="relative space-y-0">
            {steps.map((step, i) => {
              const prev = steps[i - 1];
              const newIteration = prev && prev.iteration !== step.iteration;
              return (
                <li key={step.id} className="animate-[step-in_150ms_ease-out]">
                  {newIteration && (
                    <div className="flex items-center gap-2 py-3 pl-[26px] text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase">
                      <span className="h-px w-6 bg-border" />
                      Iteration {step.iteration}
                      <span className="h-px flex-1 bg-border" />
                    </div>
                  )}
                  <div className="relative flex gap-3">
                    {i < steps.length - 1 && (
                      <span
                        className="absolute top-2 bottom-0 left-[5.5px] w-px bg-border"
                        aria-hidden
                      />
                    )}
                    <Marker step={step} />
                    <div className="min-w-0 flex-1 pb-4">
                      <p
                        className={cn(
                          "text-xs leading-4 font-medium",
                          step.status === "active" ? "text-accent" : "text-foreground",
                        )}
                      >
                        {step.label}
                        {step.node === "decision" && step.caption && (
                          <span className="text-accent"> → {step.caption}</span>
                        )}
                      </p>
                      {step.node !== "decision" && step.caption && (
                        <p className="mt-1 font-mono text-[11px] leading-4 text-muted-foreground">
                          {step.caption}
                        </p>
                      )}
                      {step.detail && (
                        <p className="mt-1 font-mono text-[11px] leading-4 text-muted-foreground">
                          {step.detail}
                        </p>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </div>
  );
}
