from typing import TypeVar

from groq import GroqError
from pydantic import BaseModel

from app.llm.client import get_llm

T = TypeVar("T", bound=BaseModel)


def call_structured(prompt: str, schema: type[T]) -> T:
    """Call the LLM constrained to a Pydantic schema.

    Model history worth knowing if this ever breaks again:

    - openai/gpt-oss-120b (previous model) failed the default
      with_structured_output() (method="function_calling") — it wouldn't
      reliably call the forced tool, and Groq rejected that with 'Tool
      choice is required, but model did not call a tool'. Working around
      it meant forcing method="json_mode", which brought its own problems:
      Groq's json_mode requires the literal word "json" in the prompt or
      it 400s, and json_mode only guarantees valid JSON, not the *shape*
      asked for — it doesn't enforce field names or nested structure, so
      we had to hand-dump the full schema.model_json_schema() into the
      prompt text just to get the model to follow it.
    - qwen/qwen3.8-27b (current model) supports real function_calling
      correctly — verified directly — so none of the above applies. Using
      the default method here means the schema goes through the API's
      native tool-definition mechanism instead of being dumped as raw text
      into the prompt. That distinction matters: qwen, given the same
      raw-schema-dump-in-prompt approach gpt-oss-120b needed, got
      confused and echoed the schema definition itself back as if it were
      the answer, rather than an instance of it. Don't reintroduce
      method="json_mode"/the schema dump unless a future model needs it
      the way gpt-oss-120b did — check with a real test first, the way
      this was found, rather than assuming.

    Retry-with-backoff stays regardless of model: a real production run
    hit "413 Request too large... tokens per minute (TPM): Limit 8000"
    from Groq's free tier — a ROLLING rate limit across all recent calls
    within 60s, not a single-request size cap. 11 real calls for one
    research question can exceed that budget even with reasonably-sized
    prompts, since Groq is fast enough to fire them all within the same
    minute window. Groq maps this to the generic APIStatusError (413),
    not the narrower RateLimitError (429 only), so we retry on GroqError
    to catch both. with_retry()'s *default* backoff (initial=1s,
    exp_base=2) only spans ~7-10s total across 4 attempts — nowhere near
    enough to clear a 60s rolling window — so initial=15s is set
    explicitly to give retries a realistic chance of landing after the
    window resets.
    """
    llm = get_llm().with_structured_output(schema).with_retry(
        retry_if_exception_type=(GroqError,),
        wait_exponential_jitter=True,
        exponential_jitter_params={"initial": 15, "max": 60},
        stop_after_attempt=4,
    )
    return llm.invoke(prompt)
