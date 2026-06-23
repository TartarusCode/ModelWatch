import asyncio
import os
from typing import TypedDict
from urllib.parse import quote

import httpx

MODELS_URL = "https://openrouter.ai/api/v1/models"
DESIGN_ARENA_URL = (
    "https://openrouter.ai/api/frontend/v1/private/design-arena-benchmarks"
)
ARTIFICIAL_ANALYSIS_URL = (
    "https://openrouter.ai/api/frontend/v1/private/artificial-analysis-benchmarks"
)

DEFAULT_CONCURRENCY = 12
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_RETRIES = 2


class FetchOptions(TypedDict, total=False):
    api_key: str | None
    concurrency: int
    timeout_seconds: float
    retries: int


def _auth_headers(api_key: str | None) -> dict[str, str]:
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}
    return {}


async def fetch_models(client: httpx.AsyncClient) -> list[dict[str, object]]:
    response = await client.get(MODELS_URL)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("models response missing data array")
    return [item for item in data if isinstance(item, dict)]


async def _fetch_json_with_retries(
    client: httpx.AsyncClient,
    url: str,
    retries: int,
) -> dict[str, object]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            raise ValueError("response is not an object")
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                await asyncio.sleep(0.5 * (attempt + 1))
    raise last_error or RuntimeError("fetch failed")


async def fetch_design_arena(
    client: httpx.AsyncClient,
    model_id: str,
    retries: int,
) -> tuple[dict[str, object] | None, str | None]:
    slug = quote(model_id, safe="")
    url = f"{DESIGN_ARENA_URL}?slug={slug}"
    try:
        payload = await _fetch_json_with_retries(client, url, retries)
        data = payload.get("data")
        if isinstance(data, dict):
            return data, None
        return None, "unexpected response shape"
    except Exception as exc:
        return None, str(exc)


async def fetch_artificial_analysis(
    client: httpx.AsyncClient,
    model_id: str,
    retries: int,
) -> tuple[list[dict[str, object]] | None, str | None]:
    slug = quote(model_id, safe="")
    url = f"{ARTIFICIAL_ANALYSIS_URL}?slug={slug}"
    try:
        payload = await _fetch_json_with_retries(client, url, retries)
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)], None
        return None, "unexpected response shape"
    except Exception as exc:
        return None, str(exc)


async def _fetch_model_benchmarks(
    client: httpx.AsyncClient,
    canonical_slug: str,
    retries: int,
    semaphore: asyncio.Semaphore,
) -> dict[str, object]:
    async with semaphore:
        design_data, design_error = await fetch_design_arena(
            client, canonical_slug, retries
        )
        aa_data, aa_error = await fetch_artificial_analysis(
            client, canonical_slug, retries
        )
    return {
        "canonical_slug": canonical_slug,
        "design_arena": design_data,
        "design_arena_error": design_error,
        "artificial_analysis": aa_data,
        "artificial_analysis_error": aa_error,
    }


async def fetch_all_benchmarks(
    canonical_slugs: list[str],
    options: FetchOptions | None = None,
) -> list[dict[str, object]]:
    opts = options or {}
    api_key = opts.get("api_key") or os.environ.get("OPENROUTER_API_KEY")
    concurrency = opts.get("concurrency", DEFAULT_CONCURRENCY)
    timeout_seconds = opts.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    retries = opts.get("retries", DEFAULT_RETRIES)
    semaphore = asyncio.Semaphore(concurrency)
    headers = _auth_headers(api_key)
    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        tasks = [
            _fetch_model_benchmarks(client, canonical_slug, retries, semaphore)
            for canonical_slug in canonical_slugs
        ]
        return await asyncio.gather(*tasks)


async def fetch_models_async(options: FetchOptions | None = None) -> list[dict[str, object]]:
    opts = options or {}
    api_key = opts.get("api_key") or os.environ.get("OPENROUTER_API_KEY")
    timeout_seconds = opts.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    headers = _auth_headers(api_key)
    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        return await fetch_models(client)
