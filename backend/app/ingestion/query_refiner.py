import re

from stop_words import get_stop_words

_STOP_WORDS = set(get_stop_words("en"))
# The standard list covers general filler ("i", "want", "about", "find",
# "using", "on", ...) but not words that are only filler in THIS specific
# context — "papers"/"search"/"studies" are real content words in general
# English, but every request here implicitly means "find papers", so they
# add nothing to an arXiv query and should always be stripped too.
_EXTRA_FILLER = {"papers", "paper", "articles", "article", "studies", "study", "search", "searching"}
_WORD_RE = re.compile(r"[a-zA-Z0-9][\w-]*")


def refine_search_query(raw_topic: str) -> str:
    """arXiv's search API does literal term matching, not natural-language
    understanding — proved empirically that a full sentence like "i want
    about quantum computing" returns completely unrelated results (particle
    physics, gravitational waves), while "quantum computing" alone returns
    exactly on-topic papers.

    Strips filler words via a static stopword list (the `stop-words`
    package) instead of an LLM call — free, instant, no API dependency.
    Started as an LLM call (call_structured against a Pydantic schema);
    switched to this after confirming the actual failure mode is just
    filler WORDS in fairly direct phrasing, not full alternate wording an
    LLM would be needed to rewrite — a static list handles that case fully
    and is strictly cheaper. Tradeoff: it can't handle an indirect
    description that never names the topic (e.g. "how neural nets handle
    graph-structured data" instead of "graph neural networks") the way an
    LLM could; accepted as out of scope for this pass.
    """
    words = _WORD_RE.findall(raw_topic.lower())
    kept = [w for w in words if w not in _STOP_WORDS and w not in _EXTRA_FILLER]
    return " ".join(kept) if kept else raw_topic.strip()
