from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import GroqError

from app.api.routes.corpus import router as corpus_router
from app.api.routes.research import router as research_router
from app.llm.client import get_llm

app = FastAPI(title="Research Paper Agent")

# Frontend (Vite/TanStack dev server) runs on a different port than this API
# during local dev — the browser blocks cross-origin fetches without this.
# Confirmed by actually checking: this repo's dev server binds 8080, not
# TanStack's usual 3000 or plain Vite's 5173 (the @lovable.dev config
# wrapper must set it explicitly) — 3000/5173 kept too in case that changes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080", "http://127.0.0.1:8080",
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)
app.include_router(corpus_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug/llm-ping")
def llm_ping():
    llm = get_llm()
    try:
        response = llm.invoke("Reply with exactly one word: pong")
    except GroqError as e:
        raise HTTPException(status_code=502, detail=f"Groq request failed: {e}") from e
    return {"reply": response.content}
