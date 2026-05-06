"""
Ollama HTTP client — sync (Celery worker) and async (FastAPI/SSE).
Uses httpx which is already installed via fastapi[standard].
"""
import json
import httpx
from app.core.config import settings

OLLAMA_GENERATE = f"{settings.OLLAMA_BASE_URL}/api/generate"


def generate_sync(prompt: str, model: str = "qwen3.5:9b", timeout: int = 180) -> str:
    """Synchronous generate — used by Celery worker."""
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(OLLAMA_GENERATE, json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 2048},
        })
        resp.raise_for_status()
        return resp.json()["response"]


async def generate_async(prompt: str, model: str = "qwen3.5:9b", timeout: int = 120) -> str:
    """Async generate — used by RRAG / chat endpoints."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(OLLAMA_GENERATE, json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 2048},
        })
        resp.raise_for_status()
        return resp.json()["response"]


async def stream_generate(prompt: str, model: str = "qwen3.5:9b", timeout: int = 120):
    """Async streaming generator — yields token strings."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", OLLAMA_GENERATE, json={
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": 0.3, "num_predict": 2048},
        }) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        yield chunk.get("response", "")
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
