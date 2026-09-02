import { ExternalLink, Library } from "lucide-react";
import { groupByQuery, type CorpusPaper } from "@/lib/corpus-list";
import { Badge } from "@/components/ui/badge";

/** Opens the PDF panel on a plain left-click; lets a modified click
 * (middle-click, ctrl/cmd-click) fall through to the real arXiv link
 * underneath, same as a router <Link> would. */
function handleLinkClick(e: React.MouseEvent<HTMLAnchorElement>, onSelect: () => void) {
  if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  e.preventDefault();
  onSelect();
}

export function CorpusSidebar({
  papers,
  error,
  onSelectPaper,
}: {
  papers: CorpusPaper[] | null;
  error: string | null;
  onSelectPaper: (paper: { paperId: string; title: string }) => void;
}) {
  return (
    <aside className="flex h-full flex-col bg-panel/75">
      <div className="flex h-[60px] shrink-0 items-center gap-2.5 border-b border-border/70 px-5">
        <span className="grid size-8 place-items-center rounded-xl bg-panel-raised text-accent">
          <Library className="size-4" />
        </span>
        <div>
          <h2 className="text-xs font-semibold tracking-tight">Library</h2>
          <p className="text-[10px] text-muted-foreground">Your paper collection</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-5">
        {error && <p className="text-xs text-destructive">Couldn't load papers: {error}</p>}
        {!error && !papers && <p className="text-xs text-muted-foreground">Loading papers…</p>}
        {!error && papers && papers.length === 0 && (
          <p className="text-xs text-muted-foreground">No papers ingested yet.</p>
        )}
        {!error && papers && papers.length > 0 && (
          <div className="space-y-6">
            {groupByQuery(papers).map(({ query, papers: group }) => (
              <div key={query ?? "__none__"}>
                <p className="mb-2 px-2 text-[10px] font-semibold tracking-[0.1em] text-muted-foreground uppercase">
                  {query ? (
                    <span className="font-mono text-accent italic">"{query}"</span>
                  ) : (
                    "keywords unknown (ingested before this was tracked)"
                  )}
                </p>
                <ul className="space-y-1.5">
                  {group.map((p) => (
                    <li key={p.paperId}>
                      <a
                        href={`https://arxiv.org/abs/${p.paperId}`}
                        onClick={(e) =>
                          handleLinkClick(e, () =>
                            onSelectPaper({ paperId: p.paperId, title: p.title }),
                          )
                        }
                        className="group flex items-baseline gap-2 rounded-xl px-2 py-2 text-xs transition-all hover:bg-panel-raised hover:shadow-sm"
                      >
                        <Badge
                          variant="outline"
                          className="shrink-0 rounded-full border-accent/60 px-1.5 py-px font-mono text-[10px] text-accent"
                        >
                          {p.paperId}
                        </Badge>
                        <span className="min-w-0 flex-1 truncate text-foreground underline-offset-2 group-hover:underline">
                          {p.title}
                        </span>
                        <ExternalLink className="size-3 shrink-0 self-center text-muted-foreground/60 transition-colors group-hover:text-accent" />
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
