import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 600/80 confirmed correct after switching the embedding model to BGE-M3
# (8192-token capacity) — the earlier "shrink to 200" plan was only needed
# to fit all-MiniLM-L6-v2's 256-token limit, which no longer applies.
CHUNK_SIZE_TOKENS = 600
CHUNK_OVERLAP_TOKENS = 80

# A trailing chunk this small or smaller is mostly the previous chunk's
# overlap repeated — e.g. a 652-token section produces a 650-token chunk
# plus an 82-token "remainder" chunk, of which 80 tokens are pure
# duplication and only 2 are genuinely new. Below this threshold, merge
# the remainder into the previous chunk instead of indexing a near-dupe.
MIN_CHUNK_TOKENS = 150

_encoding = tiktoken.get_encoding("cl100k_base")
_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base",
    chunk_size=CHUNK_SIZE_TOKENS,
    chunk_overlap=CHUNK_OVERLAP_TOKENS,
)


def _merge_small_tail(chunks: list[str]) -> list[str]:
    """If the last chunk is too small to be worth its own entry, fold its
    genuinely-new tokens into the previous chunk instead of keeping a
    near-duplicate chunk that's mostly repeated overlap.

    Can't just concatenate chunks[-2] + chunks[-1] — chunks[-1] already
    contains the last CHUNK_OVERLAP_TOKENS tokens of chunks[-2] at its
    start (that's what overlap means), so a naive concat would duplicate
    that stretch a second time. Skip past the overlapping prefix first.
    """
    if len(chunks) < 2:
        return chunks

    last_tokens = _encoding.encode(chunks[-1])
    if len(last_tokens) > MIN_CHUNK_TOKENS:
        return chunks

    new_tail_tokens = last_tokens[CHUNK_OVERLAP_TOKENS:]
    new_tail_text = _encoding.decode(new_tail_tokens)
    merged_last = chunks[-2] + " " + new_tail_text
    return chunks[:-2] + [merged_last]


def chunk_text(text: str) -> list[str]:
    """Phase 0 crude version: plain token-count chunking, no section
    awareness. Real section-aware chunking (via GROBID structure) is
    Phase 1 — this just proves the pipeline end to end.
    """
    chunks = _splitter.split_text(text)
    return _merge_small_tail(chunks)
