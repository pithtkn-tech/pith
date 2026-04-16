"""
Pith Proxy Router — Core request handler.

Flow:
1. Receive OpenAI-compatible request (/v1/chat/completions)
2. Detect & sanitize injection attempts (19 languages)
3. Optimize prompt (rule-based, <1ms, 6 languages)
4. Count tokens (before/after)
5. Forward to real LLM API
6. Stream response back
7. Log savings

Works with any OpenAI-compatible API: OpenAI, Anthropic (via proxy),
Groq, Together, Ollama, LM Studio, vLLM, etc.

Just swap your base_url:
    base_url = "http://localhost:8000/v1"
"""

import time
import httpx
import json
from .optimizer import optimize_messages
from .injection import InjectionResult
from .counter import count_tokens
from .config import get_settings

settings = get_settings()

# Reusable async HTTP client
_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    return _client


async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None


async def proxy_chat_completion(request_body: dict, headers: dict) -> dict:
    """
    Process a chat completion request through the optimization pipeline.

    Args:
        request_body: OpenAI-compatible request body with 'messages', 'model', etc.
        headers: Original request headers (Authorization, etc.)

    Returns:
        dict with keys: response, stats, injection_result
    """
    messages = request_body.get("messages", [])
    model = request_body.get("model", "gpt-4o-mini")
    stream = request_body.get("stream", False)

    # --- Step 1: Optimize messages ---
    t0 = time.perf_counter()
    optimized, injection_result = optimize_messages(messages)
    optimize_ms = (time.perf_counter() - t0) * 1000

    # --- Step 2: Handle injection ---
    if injection_result and injection_result.is_injection:
        action = settings.INJECTION_ACTION
        if action == "block":
            return {
                "error": "Request blocked: potential prompt injection detected",
                "injection": {
                    "score": injection_result.score,
                    "patterns": injection_result.matched_patterns,
                    "layer": injection_result.layer,
                },
                "blocked": True,
            }
        # sanitize and log are handled — continue with sanitized messages

    # --- Step 3: Count tokens ---
    original_tokens = count_tokens(messages)
    optimized_tokens = count_tokens(optimized)
    saved_tokens = original_tokens - optimized_tokens
    saved_percent = (saved_tokens / original_tokens * 100) if original_tokens > 0 else 0

    # --- Step 4: Forward to LLM ---
    # Determine target URL
    target_base = _extract_base_url(headers) or settings.DEFAULT_BASE_URL
    target_url = f"{target_base}/chat/completions"

    # Build forwarding headers
    forward_headers = {
        "Content-Type": "application/json",
    }
    auth = headers.get("authorization") or headers.get("Authorization")
    if auth:
        forward_headers["Authorization"] = auth
    elif settings.DEFAULT_API_KEY:
        forward_headers["Authorization"] = f"Bearer {settings.DEFAULT_API_KEY}"

    # Build forwarded body
    forward_body = {**request_body, "messages": optimized}

    client = await get_client()

    if stream:
        return {
            "stream": True,
            "target_url": target_url,
            "forward_headers": forward_headers,
            "forward_body": forward_body,
            "stats": {
                "original_tokens": original_tokens,
                "optimized_tokens": optimized_tokens,
                "saved_tokens": saved_tokens,
                "saved_percent": round(saved_percent, 1),
                "optimize_ms": round(optimize_ms, 2),
            },
            "injection": _injection_to_dict(injection_result),
        }

    # Non-streaming
    try:
        resp = await client.post(
            target_url,
            headers=forward_headers,
            json=forward_body,
            timeout=120.0,
        )
        response_data = resp.json()
    except Exception as e:
        return {"error": f"Upstream LLM error: {str(e)}", "blocked": False}

    return {
        "response": response_data,
        "stats": {
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "saved_tokens": saved_tokens,
            "saved_percent": round(saved_percent, 1),
            "optimize_ms": round(optimize_ms, 2),
            "model": model,
        },
        "injection": _injection_to_dict(injection_result),
        "blocked": False,
    }


def _extract_base_url(headers: dict) -> str | None:
    """Extract target base URL from X-Pith-Target header."""
    return headers.get("x-pith-target") or headers.get("X-Pith-Target")


def _injection_to_dict(result: InjectionResult | None) -> dict | None:
    if result is None:
        return None
    return {
        "is_injection": result.is_injection,
        "score": result.score,
        "patterns": result.matched_patterns,
        "layer": result.layer,
    }
