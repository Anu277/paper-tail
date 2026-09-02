import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ChatView } from "@/components/ChatView";
import { CorpusBuilder } from "@/components/CorpusBuilder";
import { CorpusSidebar } from "@/components/CorpusSidebar";
import { PdfViewerPanel } from "@/components/PdfViewerPanel";
import { SplashScreen } from "@/components/SplashScreen";
import { fetchCorpus, type CorpusPaper } from "@/lib/corpus-list";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "PAPERTail" },
      {
        name: "description",
        content:
          "Chat with your arXiv papers and see exactly how the agent found each answer, step by step.",
      },
      {
        property: "og:title",
        content: "PAPERTail",
      },
      {
        property: "og:description",
        content:
          "Chat with your arXiv papers and see exactly how the agent found each answer, step by step.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  const [builderOpen, setBuilderOpen] = useState(false);
  const [corpusRefreshKey, setCorpusRefreshKey] = useState(0);
  // Do not render the animated splash during SSR. Otherwise the browser starts
  // its CSS animation from the server HTML, then starts it again when React
  // hydrates the client tree, making the intro appear to play twice.
  const [showSplash, setShowSplash] = useState(false);
  const [selectedPaper, setSelectedPaper] = useState<{
    paperId: string;
    title: string;
  } | null>(null);
  const [papers, setPapers] = useState<CorpusPaper[] | null>(null);
  const [papersError, setPapersError] = useState<string | null>(null);

  useEffect(() => {
    setShowSplash(true);
  }, []);

  // Fetched once here (not inside CorpusSidebar) so ChatView can also
  // resolve a [paper_id] citation to its real title when opening the PDF
  // panel from a chat answer, without a second duplicate fetch.
  useEffect(() => {
    let cancelled = false;
    fetchCorpus()
      .then((p) => !cancelled && setPapers(p))
      .catch(
        (e) =>
          !cancelled && setPapersError(e instanceof Error ? e.message : "Failed to load corpus"),
      );
    return () => {
      cancelled = true;
    };
  }, [corpusRefreshKey]);

  return (
    <>
      {showSplash && <SplashScreen onDone={() => setShowSplash(false)} />}
      <ResizablePanelGroup direction="horizontal" className="h-screen bg-background">
        <ResizablePanel defaultSize={280} minSize={220} maxSize={480} className="min-w-0">
          <CorpusSidebar papers={papers} error={papersError} onSelectPaper={setSelectedPaper} />
        </ResizablePanel>
        <ResizableHandle withHandle />

        <ResizablePanel minSize={420} className="min-w-0">
          <div className="flex h-full flex-col">
            <ChatView
              papers={papers}
              onOpenPaper={setSelectedPaper}
              onAddPapers={() => setBuilderOpen(true)}
            />
            <CorpusBuilder
              open={builderOpen}
              onClose={() => setBuilderOpen(false)}
              onBuildComplete={() => setCorpusRefreshKey((k) => k + 1)}
            />
          </div>
        </ResizablePanel>

        {selectedPaper && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={480} minSize={340} maxSize={900} className="min-w-0">
              <PdfViewerPanel paper={selectedPaper} onClose={() => setSelectedPaper(null)} />
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>
    </>
  );
}
