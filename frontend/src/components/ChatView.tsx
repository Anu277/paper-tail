import { useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  BookPlus,
  Bot,
  Check,
  Copy,
  FileSearch,
  Plus,
  Route as RouteIcon,
  Sparkles,
  User,
} from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { ThoughtProcess } from "./ThoughtProcess";
import { runResearch, IS_DEMO, type TraceStep } from "@/lib/agent-stream";
import type { CorpusPaper } from "@/lib/corpus-list";

type OpenPaper = (paper: { paperId: string; title: string }) => void;

type Turn = {
  id: string;
  question: string;
  steps: TraceStep[];
  answer?: string;
  error?: string;
  running: boolean;
};

// The backend cites sources as plain [paper_id] brackets, not real markdown
// links — turn them into fake links first (#cite:...) so real markdown
// parsing carries them through, then render that specific href as a pill
// instead of a normal <a> in the component overrides below.
const CITATION_RE = /\[([\w.-]+)\](?!\()/g;

function linkifyCitations(markdown: string): string {
  return markdown.replace(CITATION_RE, "[$1](#cite:$1)");
}

function buildMarkdownComponents(papers: CorpusPaper[] | null, onOpenPaper: OpenPaper): Components {
  return {
    a: ({ href, children }) => {
      if (href?.startsWith("#cite:")) {
        const paperId = href.slice("#cite:".length);
        const paper = papers?.find((p) => p.paperId === paperId);
        return (
          <button
            type="button"
            onClick={() => onOpenPaper({ paperId, title: paper?.title ?? paperId })}
            className="mx-0.5 inline-flex items-center rounded-full border border-accent/60 px-1.5 py-px font-mono text-[10px] text-accent transition-colors hover:bg-accent/10"
          >
            {paperId}
          </button>
        );
      }
      return (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="text-accent underline underline-offset-2"
        >
          {children}
        </a>
      );
    },
    h1: ({ children }) => (
      <h3 className="mt-4 mb-1.5 text-sm font-semibold first:mt-0">{children}</h3>
    ),
    h2: ({ children }) => (
      <h3 className="mt-4 mb-1.5 text-sm font-semibold first:mt-0">{children}</h3>
    ),
    h3: ({ children }) => (
      <h4 className="mt-3 mb-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {children}
      </h4>
    ),
    p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
    ul: ({ children }) => <ul className="mb-3 ml-4 list-disc space-y-1 last:mb-0">{children}</ul>,
    ol: ({ children }) => (
      <ol className="mb-3 ml-4 list-decimal space-y-1 last:mb-0">{children}</ol>
    ),
    li: ({ children }) => <li className="leading-6">{children}</li>,
    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
    code: ({ children }) => (
      <code className="rounded bg-panel-raised px-1 py-px font-mono text-[11px] text-accent">
        {children}
      </code>
    ),
    table: ({ children }) => (
      <div className="mb-3 overflow-x-auto rounded-lg border border-border last:mb-0">
        <table className="w-full text-left text-xs">{children}</table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-panel-raised">{children}</thead>,
    th: ({ children }) => (
      <th className="border-b border-border px-2.5 py-1.5 font-medium text-muted-foreground">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="border-b border-border/60 px-2.5 py-1.5 align-top">{children}</td>
    ),
  };
}

/** Renders the agent's real markdown report. [paper_id] citations become
 * clickable pills that open that paper's PDF panel, resolving the real
 * title from the already-fetched corpus list where available. */
function AnswerBody({
  markdown,
  papers,
  onOpenPaper,
}: {
  markdown: string;
  papers: CorpusPaper[] | null;
  onOpenPaper: OpenPaper;
}) {
  return (
    <div className="text-sm leading-6">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={buildMarkdownComponents(papers, onOpenPaper)}
      >
        {linkifyCitations(markdown)}
      </ReactMarkdown>
    </div>
  );
}

const SUGGESTIONS = [
  "Summarize the key findings across my papers",
  "What are the open research questions?",
  "Compare the methods used in these papers",
];

function EmptyState({ onSuggestion }: { onSuggestion: (question: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center sm:py-28">
      <span className="grid size-14 place-items-center rounded-2xl border border-accent/30 bg-accent/10 shadow-[0_0_40px_var(--accent-dim)]">
        <Sparkles className="size-5 text-accent" />
      </span>
      <p className="mt-6 text-[10px] font-bold tracking-[0.22em] text-accent uppercase">
        Paper intelligence
      </p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight">
        What would you like to explore?
      </h2>
      <p className="mt-3 max-w-md text-sm leading-6 text-muted-foreground">
        You can see exactly how the agent got to each answer: the searches it ran, what it found,
        and how it double-checked its own claims.
      </p>
      <div className="mt-8 grid w-full max-w-2xl gap-2 text-left sm:grid-cols-3">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => onSuggestion(suggestion)}
            className="group rounded-2xl border border-border bg-panel p-4 text-left text-xs leading-5 text-muted-foreground transition-all hover:-translate-y-0.5 hover:border-accent/70 hover:bg-panel-raised hover:text-foreground"
          >
            <FileSearch className="mb-5 size-4 text-accent transition-transform group-hover:scale-110" />
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

const CHAT_STORAGE_KEY = "papertail.chat-history";
const CHAT_SESSIONS_STORAGE_KEY = "papertail.chat-sessions";
// Caps how much actually gets written to localStorage — otherwise a long-
// running chat habit grows this forever. In-memory `turns` during the
// current tab session is NOT capped (that's just JS heap, not disk), only
// what gets persisted for the next reload.
const MAX_STORED_TURNS = 40;

type ChatSession = {
  id: string;
  title: string;
  turns: Turn[];
  updatedAt: number;
};

function makeSession(): ChatSession {
  return {
    id: crypto.randomUUID(),
    title: "New research chat",
    turns: [],
    updatedAt: Date.now(),
  };
}

function loadSessions(): ChatSession[] {
  try {
    const sessionsRaw = localStorage.getItem(CHAT_SESSIONS_STORAGE_KEY);
    if (sessionsRaw) {
      const sessions = JSON.parse(sessionsRaw) as ChatSession[];
      return sessions.map((session) => ({
        ...session,
        turns: session.turns.map((t) => (t.running ? { ...t, running: false } : t)),
      }));
    }
    const raw = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Turn[];
    // A turn still marked "running" means the tab closed mid-stream —
    // there's no connection to resume, so it can only ever be stuck.
    return [
      {
        ...makeSession(),
        title: parsed[0]?.question.slice(0, 36) || "Previous research chat",
        turns: parsed.map((t) => (t.running ? { ...t, running: false } : t)),
      },
    ];
  } catch {
    return [];
  }
}

function saveSessions(sessions: ChatSession[]) {
  // Progressively trim harder if a write still doesn't fit (e.g. one turn's
  // report happens to be huge) rather than giving up on persistence entirely
  // the moment the quota is hit once.
  for (const keep of [MAX_STORED_TURNS, 20, 8, 2]) {
    try {
      localStorage.setItem(CHAT_SESSIONS_STORAGE_KEY, JSON.stringify(sessions.slice(-keep)));
      return;
    } catch {
      // try the next, smaller cap
    }
  }
  // Private browsing / storage disabled entirely — losing history beats crashing.
}

export function ChatView({
  papers,
  onOpenPaper,
  onAddPapers,
}: {
  papers: CorpusPaper[] | null;
  onOpenPaper: OpenPaper;
  onAddPapers: () => void;
}) {
  const [initialState] = useState(() => {
    const saved = loadSessions();
    const sessions = saved.length ? saved : [makeSession()];
    return { sessions, activeSessionId: sessions[0].id };
  });
  const [sessions, setSessions] = useState<ChatSession[]>(initialState.sessions);
  const [activeSessionId, setActiveSessionId] = useState(initialState.activeSessionId);
  const [input, setInput] = useState("");
  const [copiedTurnId, setCopiedTurnId] = useState<string | null>(null);
  const activeSession = sessions.find((session) => session.id === activeSessionId) ?? sessions[0];
  const turns = activeSession.turns;
  const busy = sessions.some((session) => session.turns.some((turn) => turn.running));
  const scroller = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const abort = useRef<(() => void) | null>(null);

  useEffect(() => composer.current?.focus(), []);
  useEffect(() => () => abort.current?.(), []);
  useEffect(() => {
    scroller.current?.scrollTo({
      top: scroller.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns]);
  useEffect(() => saveSessions(sessions), [sessions]);

  const updateTurns = (sessionId: string, update: (turns: Turn[]) => Turn[]) => {
    setSessions((previous) =>
      previous.map((session) =>
        session.id === sessionId
          ? { ...session, turns: update(session.turns), updatedAt: Date.now() }
          : session,
      ),
    );
  };

  const newChat = () => {
    const session = makeSession();
    setSessions((previous) => [session, ...previous]);
    setActiveSessionId(session.id);
    setInput("");
    requestAnimationFrame(() => composer.current?.focus());
  };

  const copyAnswer = async (turnId: string, answer: string) => {
    await navigator.clipboard?.writeText(answer);
    setCopiedTurnId(turnId);
    window.setTimeout(() => setCopiedTurnId(null), 1500);
  };

  const send = () => {
    const question = input.trim();
    if (!question || busy) return;
    const id = crypto.randomUUID();
    const sessionId = activeSession.id;
    setInput("");
    setSessions((previous) =>
      previous.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              title: session.turns.length === 0 ? question.slice(0, 42) : session.title,
              turns: [...session.turns, { id, question, steps: [], running: true }],
              updatedAt: Date.now(),
            }
          : session,
      ),
    );

    const patch = (fn: (t: Turn) => Turn) =>
      updateTurns(sessionId, (previous) => previous.map((t) => (t.id === id ? fn(t) : t)));

    abort.current = runResearch(question, (event) => {
      if (event.type === "step") {
        patch((t) => ({
          ...t,
          steps: [
            ...t.steps.map((s) => ({ ...s, status: "done" as const })),
            { ...event.step, status: "active" as const },
          ],
        }));
      } else if (event.type === "answer") {
        patch((t) => ({
          ...t,
          answer: event.markdown,
          steps: t.steps.map((s) => ({ ...s, status: "done" as const })),
        }));
      } else if (event.type === "error") {
        patch((t) => ({ ...t, error: event.message, running: false }));
      } else {
        patch((t) => ({
          ...t,
          running: false,
          steps: t.steps.map((s) => ({ ...s, status: "done" as const })),
        }));
      }
    });
    requestAnimationFrame(() => composer.current?.focus());
  };

  return (
    <>
      <header className="border-b border-border/70 bg-background/80 px-5 backdrop-blur-xl sm:px-8">
        <div className="mx-auto flex w-full max-w-4xl items-center gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-accent text-accent-foreground shadow-[0_4px_18px_var(--accent-dim)]">
            <RouteIcon className="size-4" />
          </span>
          <div className="min-w-0 flex-1 py-3">
            <h1 className="text-base font-semibold tracking-tight">
              Paper <span className="text-accent">Tail</span>
            </h1>
            <p className="truncate text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
              {activeSession.title}
            </p>
          </div>
          <button
            onClick={newChat}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-panel px-3 py-2.5 text-xs font-semibold transition-colors hover:border-accent hover:text-accent disabled:opacity-40"
          >
            <Plus className="size-3.5" /> New chat
          </button>
          <button
            onClick={onAddPapers}
            className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-3.5 py-2.5 text-xs font-bold text-accent-foreground shadow-[0_4px_18px_var(--accent-dim)] transition-transform hover:scale-[1.02]"
          >
            <BookPlus className="size-3.5" />
            Add Papers
          </button>
        </div>
        {sessions.length > 1 && (
          <div className="mx-auto flex w-full max-w-4xl gap-2 overflow-x-auto border-t border-border/50 py-2.5">
            {sessions.slice(0, 8).map((session) => (
              <button
                key={session.id}
                onClick={() => setActiveSessionId(session.id)}
                disabled={busy}
                className={cn(
                  "max-w-48 shrink-0 truncate rounded-full border px-3 py-1.5 text-[11px] transition-colors",
                  session.id === activeSession.id
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-border bg-panel text-muted-foreground hover:text-foreground",
                )}
              >
                {session.title}
              </button>
            ))}
          </div>
        )}
      </header>
      <div ref={scroller} className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-4xl px-5 pt-8 pb-8 sm:px-8">
          {turns.length === 0 ? (
            <EmptyState onSuggestion={(question) => setInput(question)} />
          ) : (
            <div className="space-y-8">
              {turns.map((turn) => (
                <div key={turn.id} className="space-y-5">
                  <div className="flex items-end justify-end gap-2.5">
                    <div className="max-w-[80%] animate-[bubble-in_260ms_ease-out] rounded-3xl rounded-br-md bg-accent px-5 py-3 text-sm leading-6 text-accent-foreground shadow-[0_8px_28px_var(--accent-dim)]">
                      {turn.question}
                    </div>
                    <span className="grid size-8 shrink-0 place-items-center rounded-full bg-panel-raised text-accent ring-1 ring-border">
                      <User className="size-3.5" />
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <span className="grid size-8 shrink-0 place-items-center rounded-full border border-accent/30 bg-accent/10 text-accent shadow-[0_0_20px_var(--accent-dim)]">
                      <Bot className="size-4" />
                    </span>
                    <div className="min-w-0 flex-1 pt-0.5">
                      <ThoughtProcess steps={turn.steps} running={turn.running} />
                      {turn.answer && (
                        <div className="animate-[bubble-in_260ms_ease-out] rounded-3xl rounded-tl-md border border-border bg-panel px-5 py-4 shadow-[0_12px_32px_rgb(0_0_0_/_0.18)]">
                          <div className="mb-3 flex items-center gap-2 text-[10px] font-bold tracking-[0.16em] text-accent uppercase">
                            <span className="size-1.5 rounded-full bg-accent" /> PAPERTail
                          </div>
                          <AnswerBody
                            markdown={turn.answer}
                            papers={papers}
                            onOpenPaper={onOpenPaper}
                          />
                          <div className="mt-4 flex items-center border-t border-border/70 pt-3">
                            <button
                              onClick={() => copyAnswer(turn.id, turn.answer!)}
                              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-panel-raised hover:text-accent"
                            >
                              {copiedTurnId === turn.id ? (
                                <Check className="size-3.5" />
                              ) : (
                                <Copy className="size-3.5" />
                              )}
                              {copiedTurnId === turn.id ? "Copied" : "Copy answer"}
                            </button>
                          </div>
                        </div>
                      )}
                      {turn.error && (
                        <p className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                          {turn.error}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border/70 bg-background/90 backdrop-blur-xl">
        <div className="mx-auto w-full max-w-4xl px-5 py-5 sm:px-8">
          <div
            className={cn(
              "flex items-end gap-3 rounded-2xl border border-border bg-panel px-4 py-3 shadow-[0_12px_36px_rgb(0_0_0_/_0.28)] transition-all focus-within:border-accent focus-within:ring-4 focus-within:ring-accent/10",
            )}
          >
            <textarea
              ref={composer}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder="Ask a question about your papers…"
              className="max-h-40 flex-1 resize-none bg-transparent py-2 text-sm leading-6 outline-none placeholder:text-muted-foreground/70"
            />
            <button
              onClick={send}
              disabled={busy || !input.trim()}
              aria-label="Send question"
              className="mb-0.5 grid size-9 shrink-0 place-items-center rounded-xl bg-accent text-accent-foreground shadow-[0_4px_14px_var(--accent-dim)] transition-transform hover:scale-105 disabled:opacity-30"
            >
              <ArrowUp className="size-4" />
            </button>
          </div>
          <p className="mt-2 text-center text-[10px] text-muted-foreground">
            {IS_DEMO
              ? "This is a demo trace. Set VITE_AGENT_API_URL to connect the real agent."
              : "Connected to the live agent."}
          </p>
        </div>
      </div>
    </>
  );
}
