"""
Ollama HTTP client — sync (Celery worker) and async (FastAPI/SSE).
Uses httpx which is already installed via fastapi[standard].
"""
import json
import re
import httpx
from app.core.config import settings

OLLAMA_GENERATE = f"{settings.OLLAMA_BASE_URL}/api/generate"

_THINK_STRIP_RE = re.compile(
    r"</?think\s*/?>[\s\S]*?</think>\s*|"
    r"<\|\s*think\s*\|>[\s\S]*?<\|\s*/\s*think\s*\|>\s*",
    flags=re.IGNORECASE,
)


def _strip_thinking(raw: str) -> str:
    """Remove <think>...</think> blocks some reasoning models leak into output."""
    return _THINK_STRIP_RE.sub("", raw).strip()


def _build_payload(prompt: str, model: str, timeout: int) -> dict:
    return {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1,
            "num_predict": getattr(settings, "OLLAMA_NUM_PREDICT", 4096),
        },
    }


def generate_sync(prompt: str, model: str = "", timeout: int | None = None) -> str:
    """Synchronous generate — used by Celery worker."""
    model = model or settings.OLLAMA_MODEL
    timeout = timeout or settings.OLLAMA_TIMEOUT
    payload = _build_payload(prompt, model, timeout)
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(OLLAMA_GENERATE, json=payload)
        resp.raise_for_status()
        return _strip_thinking(resp.json()["response"])


async def generate_async(prompt: str, model: str = "", timeout: int = 120) -> str:
    """Async generate — used by RRAG / chat endpoints."""
    model = model or settings.OLLAMA_MODEL
    payload = _build_payload(prompt, model, timeout)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(OLLAMA_GENERATE, json=payload)
        resp.raise_for_status()
        return _strip_thinking(resp.json()["response"])


async def stream_generate(prompt: str, model: str = "", timeout: int = 120):
    """Async streaming generator — yields token strings."""
    model = model or settings.OLLAMA_MODEL
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", OLLAMA_GENERATE, json={
            "model": model,
            "prompt": prompt,
            "stream": True,
            "think": False,
            "options": {
                "temperature": 0.1,
                "num_predict": getattr(settings, "OLLAMA_NUM_PREDICT", 4096),
            },
        }) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        text = chunk.get("response", "")
                        if text:
                            yield text
                    except json.JSONDecodeError:
                        continue


OLLAMA_EMBED = f"{settings.OLLAMA_BASE_URL}/api/embed"


async def get_embedding(text: str, model: str = "bge-m3", timeout: int = 30) -> list[float]:
    """Get text embedding from Ollama. Returns 1024-dim vector from bge-m3."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(OLLAMA_EMBED, json={
            "model": model,
            "input": text,
        })
        resp.raise_for_status()
        data = resp.json()
        return data["embeddings"][0]
