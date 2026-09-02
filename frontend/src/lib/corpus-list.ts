/**
 * Read-only view of what's already in the corpus — which papers are
 * ingested and which search query (topic typed into the Corpus Builder)
 * brought each one in. Separate from corpus-stream.ts, which drives a NEW
 * build; this just lists the result of builds already run.
 */

import { AGENT_API_URL } from "./agent-stream";

export type CorpusPaper = {
  paperId: string;
  title: string;
  published: string;
  /** null for papers ingested before this was tracked, or backfilled by
   * paper_id directly rather than via a search. */
  searchQuery: string | null;
};

const DEMO_CORPUS: CorpusPaper[] = [
  {
    paperId: "2607.01852",
    title: "Evaluating Chunking Strategies for Retrieval-Augmented Generation on Academic Texts",
    published: "2026-07-02",
    searchQuery: "retrieval augmented generation chunking",
  },
  {
    paperId: "2604.10021",
    title: "Fixed-Window Retrieval Baselines Revisited",
    published: "2026-04-12",
    searchQuery: "retrieval augmented generation chunking",
  },
  {
    paperId: "2512.00931",
    title: "Hybrid Dense-Sparse Retrieval for Scientific QA",
    published: "2025-12-03",
    searchQuery: "hybrid retrieval scientific qa",
  },
];

export async function fetchCorpus(): Promise<CorpusPaper[]> {
  if (!AGENT_API_URL) return DEMO_CORPUS;

  const res = await fetch(`${AGENT_API_URL}/corpus`);
  if (!res.ok) throw new Error(`Corpus fetch failed: ${res.status}`);
  const data = (await res.json()) as {
    papers: Array<{
      paper_id: string;
      title: string;
      published: string;
      search_query: string | null;
    }>;
  };
  return data.papers.map((p) => ({
    paperId: p.paper_id,
    title: p.title,
    published: p.published,
    searchQuery: p.search_query,
  }));
}

export function groupByQuery(
  papers: CorpusPaper[],
): Array<{ query: string | null; papers: CorpusPaper[] }> {
  const groups = new Map<string | null, CorpusPaper[]>();
  for (const p of papers) {
    const key = p.searchQuery;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(p);
  }
  return Array.from(groups.entries()).map(([query, papers]) => ({
    query,
    papers,
  }));
}
