import { ExternalLink, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export function PdfViewerPanel({
  paper,
  onClose,
}: {
  paper: { paperId: string; title: string } | null;
  onClose: () => void;
}) {
  if (!paper) return null;

  const pdfUrl = `https://arxiv.org/pdf/${paper.paperId}`;
  const absUrl = `https://arxiv.org/abs/${paper.paperId}`;

  return (
    <aside className="flex h-full flex-col bg-panel">
      <div className="flex h-[60px] shrink-0 items-center gap-3 border-b border-border/70 px-4">
        <a
          href={absUrl}
          target="_blank"
          rel="noreferrer"
          className="flex min-w-0 flex-1 items-baseline gap-1.5 text-accent hover:underline"
        >
          <span className="truncate text-xs font-semibold text-foreground">{paper.title}</span>
          <ExternalLink className="size-3 shrink-0" />
        </a>
        <Button
          variant="ghost"
          size="icon"
          className="size-7 shrink-0 text-muted-foreground hover:text-foreground"
          onClick={onClose}
          aria-label="Close PDF"
        >
          <X className="size-4" />
        </Button>
      </div>

      {/* Browser's native PDF.js viewer — gives scroll, zoom in/out and
          in-document search (Ctrl+F while focused inside it) with its own
          toolbar on top, for free, no PDF rendering library needed here. */}
      <iframe src={pdfUrl} title={`${paper.paperId} PDF`} className="min-h-0 flex-1 border-0" />
    </aside>
  );
}
