from pathlib import Path

from app.ingestion.chunker import chunk_text
from app.ingestion.parser import parse_pdf

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "papers" / "raw"


def build_corpus(verbose: bool = True) -> tuple[list[str], list[dict]]:
    """Parses every PDF via GROBID and chunks within each section.

    Shared by scripts/build_index.py (FAISS) and scripts/build_bm25.py —
    both need the identical texts/metadatas, and GROBID parsing is the slow
    part, so this runs it exactly once regardless of how many indexes get
    built from the result.
    """
    texts: list[str] = []
    metadatas: list[dict] = []

    for pdf_path in sorted(RAW_DIR.glob("*.pdf")):
        paper_id = pdf_path.stem
        paper = parse_pdf(str(pdf_path))
        if verbose:
            print(f"[parse] {paper_id}: {paper['title'][:60]!r} — {len(paper['sections'])} sections")

        chunk_index = 0
        for section in paper["sections"]:
            for chunk in chunk_text(section["text"]):
                texts.append(chunk)
                metadatas.append(
                    {
                        "paper_id": paper_id,
                        "chunk_id": f"{paper_id}-{chunk_index}",
                        "section": section["heading"],
                    }
                )
                if verbose:
                    preview = chunk[:60].replace("\n", " ")
                    print(f"  [{paper_id}-{chunk_index}] ({section['heading']}) {preview!r}...")
                chunk_index += 1

    return texts, metadatas
