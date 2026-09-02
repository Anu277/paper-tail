import re
import time

import requests

from app.config.settings import get_settings

OPENALEX_URL = "https://api.openalex.org/works"

# Real failure hit: a run resolving ~130 references across 5 papers
# exhausted OpenAlex's ~100-request anonymous daily quota entirely — not a
# per-minute throttle, a hard "$0 of $0.10 budget left, resets in ~10.7h"
# wall that no amount of backoff fixes. A real OPENALEX_API_KEY raises this
# to 10,000 requests/$1.00 per day (verified: 200 -> 10000 limit switching
# from anonymous+mailto to a real key). Retry-with-backoff stays in place
# for genuine transient blips, but the API key is what actually matters.
MAX_RETRIES = 4
RETRY_BACKOFF_SECONDS = 5

# OpenAlex's search treats "*" AND "?" as wildcard operators with their own
# rules, not literal characters — two separate real failures hit this:
# a title containing "90%*" 400'd with "wildcard needs at least 3 leading
# characters", and a title ending in a literal question mark ("...Human
# Experts?...") 400'd with "Wildcards (* or ?) require exact search".
# We're doing plain literal title search, not intentionally using their
# query syntax, so strip characters that mean something special to it
# rather than trying to satisfy each wildcard's own rules one at a time.
_QUERY_SYNTAX_CHARS = re.compile(r"[*?~]")


def resolve_reference(title: str) -> str | None:
    """Resolve a reference title (from GROBID's parsed bibliography) to a
    real OpenAlex work ID, e.g. 'https://openalex.org/W4411113004'.

    Verified against a real reference from our corpus: searching GROBID's
    extracted title for "Is Semantic Chunking Worth the Computational
    Cost?" returned that exact paper as the top result. Takes the top
    result without a similarity threshold — Phase 1 crude version; a
    title-similarity check would harden this against false positives on
    weaker matches, not yet built.
    """
    if not title:
        return None

    clean_title = _QUERY_SYNTAX_CHARS.sub("", title)

    settings = get_settings()
    params = {"search": clean_title, "per_page": 1}
    if settings.openalex_email:
        params["mailto"] = settings.openalex_email
    if settings.openalex_api_key:
        params["api_key"] = settings.openalex_api_key

    for attempt in range(MAX_RETRIES):
        response = requests.get(OPENALEX_URL, params=params, timeout=15)
        if response.status_code == 429:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF_SECONDS * (attempt + 1)
                print(f"  [rate limited] waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            # Still rate-limited after every retry — skip this one reference
            # rather than crashing a run that may be 20+ minutes and 100+
            # references into otherwise-successful work.
            print("  [rate limited] giving up on this reference after retries")
            return None
        response.raise_for_status()
        results = response.json().get("results", [])
        return results[0]["id"] if results else None

    return None
