"""LangSmith tracing setup. LangChain/LangGraph read LANGSMITH_* from
os.environ at call time, not from our own Settings object directly, so
this bridges the two — called once, as early as possible, from every real
entry point (the FastAPI app and the eval harness), not just app.main,
since eval runs are exactly the kind of run worth tracing too.

No-op (zero behavior/latency change) when langsmith_api_key is unset —
safe to call unconditionally.
"""

import os

from app.config.settings import get_settings


def setup_langsmith() -> None:
    settings = get_settings()
    if not settings.langsmith_api_key:
        return
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
