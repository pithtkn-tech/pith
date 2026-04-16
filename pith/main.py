"""
Pith — LLM API Proxy with Prompt Optimization & Injection Protection.

Run:
    pip install pith
    pith serve

Or:
    python -m pith.main

Then point your LLM client to http://localhost:8000/v1
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .router import proxy_chat_completion, get_client, close_client

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    features = ["rule-based optimization (6 langs)", "injection detection (19 langs)"]
    if settings.KEYBERT_ENABLED:
        features.append("KeyBERT tag extraction")
    if settings.LLMLINGUA_ENABLED:
        features.append("LLMLingua-2 compression")
    if settings.DEBERTA_ENABLED:
        features.append("DeBERTa ML injection")

    print(f"[Pith] Starting up...")
    print(f"[Pith] Features: {', '.join(features)}")
    print(f"[Pith] Listening at http://{settings.HOST}:{settings.PORT}")
    print(f"[Pith] Target: {settings.DEFAULT_BASE_URL}")
    yield
    print("[Pith] Shutting down...")
    await close_client()


app = FastAPI(
    title="Pith",
    description="LLM API proxy with prompt optimization & injection protection",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "pith",
        "version": "0.1.0",
        "features": {
            "optimizer": settings.OPTIMIZER_ENABLED,
            "injection": settings.INJECTION_ENABLED,
            "compression": settings.COMPRESSION_MODE,
            "keybert": settings.KEYBERT_ENABLED,
            "llmlingua": settings.LLMLINGUA_ENABLED,
            "deberta": settings.DEBERTA_ENABLED,
        },
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI-compatible chat completions endpoint.

    Drop-in replacement: just change your base_url to http://localhost:8000/v1

    Pith optimizes prompts and detects injection before forwarding
    to the real LLM API.
    """
    body = await request.json()
    headers = dict(request.headers)

    # Check for compression mode override
    compression = headers.get("x-pith-compression")
    if compression:
        settings.COMPRESSION_MODE = compression

    result = await proxy_chat_completion(body, headers)

    # Blocked by injection detection
    if result.get("blocked"):
        return JSONResponse(status_code=400, content=result)

    # Error
    if result.get("error") and not result.get("response"):
        return JSONResponse(status_code=502, content=result)

    # Streaming response
    if result.get("stream"):
        client = await get_client()
        upstream = await client.send(
            client.build_request(
                "POST",
                result["target_url"],
                headers=result["forward_headers"],
                json=result["forward_body"],
            ),
            stream=True,
        )
        return StreamingResponse(
            upstream.aiter_bytes(),
            status_code=upstream.status_code,
            headers={
                "Content-Type": "text/event-stream",
                "X-Pith-Saved-Tokens": str(result["stats"]["saved_tokens"]),
                "X-Pith-Saved-Percent": str(result["stats"]["saved_percent"]),
            },
        )

    # Normal response — add stats headers
    response = result.get("response", {})
    stats = result.get("stats", {})

    return JSONResponse(
        content=response,
        headers={
            "X-Pith-Saved-Tokens": str(stats.get("saved_tokens", 0)),
            "X-Pith-Saved-Percent": str(stats.get("saved_percent", 0)),
            "X-Pith-Original-Tokens": str(stats.get("original_tokens", 0)),
            "X-Pith-Optimize-Ms": str(stats.get("optimize_ms", 0)),
        },
    )


@app.get("/v1/stats")
async def stats():
    """Quick stats about optimization performance."""
    return {
        "message": "For detailed analytics, visit pithtoken.ai/dashboard",
        "optimizer_enabled": settings.OPTIMIZER_ENABLED,
        "injection_enabled": settings.INJECTION_ENABLED,
    }


def serve():
    """Start the Pith proxy server."""
    import uvicorn
    uvicorn.run(
        "pith.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    serve()
