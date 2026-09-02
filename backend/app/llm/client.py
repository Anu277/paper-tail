from collections.abc import Iterator
from functools import lru_cache
from typing import TypedDict

from langchain_groq import ChatGroq

from app.config.settings import get_settings


@lru_cache
def get_llm() -> ChatGroq:
    settings = get_settings()
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0,
        # max_tokens defaults to None here, meaning Groq's own silent
        # server-side default applies — that's what truncated a real
        # final_report mid-sentence (with a stray non-English token
        # leaking in right at the cutoff point) with no error raised.
        # Set explicitly so longer outputs like the report aren't capped.
        max_tokens=4096,
    )


class StreamEvent(TypedDict):
    type: str  # "thinking" | "answer"
    text: str


def stream_llm(prompt: str) -> Iterator[StreamEvent]:
    """Yields reasoning and answer tokens as they arrive, tagged by type.

    For real-time output to the frontend's "processing / background
    thoughts" section (a saved requirement, not built yet) — the eventual
    Answer Generator (stage 10) should use this, since its output is
    free-form text worth showing live. NOT for planner/evaluator/decision
    nodes — those need call_structured()'s validated Pydantic output before
    any of their fields can be used, so there's nothing meaningful to
    stream until the full JSON is already complete.

    gpt-oss-120b streams its chain-of-thought separately from its answer,
    in chunk.additional_kwargs['reasoning_content'] rather than
    chunk.content — confirmed by inspecting real stream chunks, this
    isn't documented anywhere obvious.
    """
    llm = get_llm()
    for chunk in llm.stream(prompt):
        reasoning = chunk.additional_kwargs.get("reasoning_content")
        if reasoning:
            yield {"type": "thinking", "text": reasoning}
        if chunk.content:
            yield {"type": "answer", "text": chunk.content}
