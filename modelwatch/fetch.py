import asyncio
import os
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TypedDict
from urllib.parse import quote

import httpx

from modelwatch.http import auth_headers

MODELS_URL = "https://openrouter.ai/api/v1/models"
DESIGN_ARENA_URL = (
    "https://openrouter.ai/api/frontend/v1/private/design-arena-benchmarks"
)
ARTIFICIAL_ANALYSIS_URL = (
    "https://openrouter.ai/api/frontend/v1/private/artificial-analysis-benchmarks"
)
BENCHMARK_SCORES_URL = "https://openrouter.ai/api/frontend/v1/stats/benchmark-scores"
EFFECTIVE_PRICING_URL = "https://openrouter.ai/api/frontend/v1/stats/effective-pricing"

DEFAULT_CONCURRENCY = 12
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_RETRIES = 2
# Throttled responses (429/503) are retried harder than other failures, and the
# whole benchmark pass gets a slow second attempt for anything that still failed
# — the private frontend endpoints rate limit a 400-model crawl otherwise.
THROTTLE_RETRIES = 4
RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
THROTTLE_STATUS_CODES = frozenset({429, 503})
MAX_RETRY_DELAY_SECONDS = 10.0
RETRY_PASS_CONCURRENCY = 2
RETRY_PASS_SPACING_SECONDS = 0.35

BENCHMARK_SOURCES = (
    "design_arena",
    "artificial_analysis",
    "benchmark_scores",
    "effective_pricing",
)


class FetchOptions(TypedDict, total=False):
    api_key: str | None
    concurrency: int
    timeout_seconds: float
    retries: int


async def fetch_models(client: httpx.AsyncClient) -> list[dict[str, object]]:
    response = await client.get(MODELS_URL)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("models response missing data array")
    return [item for item in data if isinstance(item, dict)]


def _parse_retry_after(value: str) -> float | None:
    """Seconds to wait per a Retry-After header (delta-seconds or HTTP-date)."""
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return max(0.0, float(stripped))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(stripped)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def _retry_delay_seconds(response: httpx.Response | None, attempt: int) -> float:
    """Honour Retry-After when the response carries one, else back off."""
    if response is not None:
        header = response.headers.get("Retry-After")
        if header is not None:
            parsed = _parse_retry_after(header)
            if parsed is not None:
                return min(parsed, MAX_RETRY_DELAY_SECONDS)
    base = min(2.0**attempt, 8.0)
    return base + random.uniform(0.0, base / 2.0)


async def _fetch_json_with_retries(
    client: httpx.AsyncClient,
    url: str,
    retries: int,
) -> dict[str, object]:
    last_error: Exception | None = None
    attempt = 0
    while True:
        try:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            raise ValueError("response is not an object")
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status = exc.response.status_code
            # Throttled upstreams get more patience than the caller asked for;
            # other retryable statuses keep the usual budget, and statuses that
            # will never succeed (404, 403) fail immediately.
            allowed = THROTTLE_RETRIES if status in THROTTLE_STATUS_CODES else retries
            if status not in RETRYABLE_STATUS_CODES or attempt >= allowed:
                break
            await asyncio.sleep(_retry_delay_seconds(exc.response, attempt))
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            await asyncio.sleep(_retry_delay_seconds(None, attempt))
        attempt += 1
    raise last_error or RuntimeError("fetch failed")


async def fetch_design_arena(
    client: httpx.AsyncClient,
    canonical_slug: str,
    retries: int,
) -> tuple[dict[str, object] | None, str | None]:
    slug = quote(canonical_slug, safe="")
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
    canonical_slug: str,
    retries: int,
) -> tuple[list[dict[str, object]] | None, str | None]:
    slug = quote(canonical_slug, safe="")
    url = f"{ARTIFICIAL_ANALYSIS_URL}?slug={slug}"
    try:
        payload = await _fetch_json_with_retries(client, url, retries)
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)], None
        return None, "unexpected response shape"
    except Exception as exc:
        return None, str(exc)


def benchmark_scores_url(canonical_slug: str) -> str:
    slug = quote(canonical_slug, safe="")
    return f"{BENCHMARK_SCORES_URL}?permaslug={slug}"


def effective_pricing_url(
    canonical_slug: str,
    *,
    variant: str = "standard",
) -> str:
    slug = quote(canonical_slug, safe="")
    variant_value = quote(variant, safe="")
    return f"{EFFECTIVE_PRICING_URL}?permaslug={slug}&variant={variant_value}"


def endpoints_url_for_model_id(model_id: str) -> str:
    slash = model_id.index("/")
    author = quote(model_id[:slash], safe="")
    slug = quote(model_id[slash + 1 :], safe="")
    return f"{MODELS_URL}/{author}/{slug}/endpoints"


async def fetch_benchmark_scores(
    client: httpx.AsyncClient,
    canonical_slug: str,
    retries: int,
) -> tuple[dict[str, object] | None, str | None]:
    url = benchmark_scores_url(canonical_slug)
    try:
        payload = await _fetch_json_with_retries(client, url, retries)
        data = payload.get("data")
        if isinstance(data, dict):
            return data, None
        return None, "unexpected response shape"
    except Exception as exc:
        return None, str(exc)


async def fetch_effective_pricing(
    client: httpx.AsyncClient,
    canonical_slug: str,
    retries: int,
) -> tuple[dict[str, object] | None, str | None]:
    url = effective_pricing_url(canonical_slug)
    try:
        payload = await _fetch_json_with_retries(client, url, retries)
        data = payload.get("data")
        if isinstance(data, dict):
            return data, None
        return None, "unexpected response shape"
    except Exception as exc:
        return None, str(exc)


async def fetch_provider_endpoints(
    client: httpx.AsyncClient,
    model_id: str,
    retries: int,
) -> tuple[dict[str, object] | None, str | None]:
    url = endpoints_url_for_model_id(model_id)
    try:
        payload = await _fetch_json_with_retries(client, url, retries)
        data = payload.get("data")
        if isinstance(data, dict):
            return data, None
        return None, "unexpected response shape"
    except Exception as exc:
        return None, str(exc)


async def _fetch_model_provider_endpoints(
    client: httpx.AsyncClient,
    model_id: str,
    retries: int,
    semaphore: asyncio.Semaphore,
) -> dict[str, object]:
    async with semaphore:
        endpoints_data, endpoints_error = await fetch_provider_endpoints(
            client,
            model_id,
            retries,
        )
    return {
        "model_id": model_id,
        "endpoints": endpoints_data,
        "endpoints_error": endpoints_error,
    }


async def fetch_all_provider_endpoints(
    model_ids: list[str],
    options: FetchOptions | None = None,
) -> list[dict[str, object]]:
    opts = options or {}
    api_key = opts.get("api_key") or os.environ.get("OPENROUTER_API_KEY")
    concurrency = opts.get("concurrency", DEFAULT_CONCURRENCY)
    timeout_seconds = opts.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    retries = opts.get("retries", DEFAULT_RETRIES)
    semaphore = asyncio.Semaphore(concurrency)
    headers = auth_headers(api_key)
    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        tasks = [
            _fetch_model_provider_endpoints(client, model_id, retries, semaphore)
            for model_id in model_ids
        ]
        return await asyncio.gather(*tasks)


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
        benchmark_scores_data, benchmark_scores_error = await fetch_benchmark_scores(
            client,
            canonical_slug,
            retries,
        )
        effective_pricing_data, effective_pricing_error = await fetch_effective_pricing(
            client,
            canonical_slug,
            retries,
        )
    return {
        "canonical_slug": canonical_slug,
        "design_arena": design_data,
        "design_arena_error": design_error,
        "artificial_analysis": aa_data,
        "artificial_analysis_error": aa_error,
        "benchmark_scores": benchmark_scores_data,
        "benchmark_scores_error": benchmark_scores_error,
        "effective_pricing": effective_pricing_data,
        "effective_pricing_error": effective_pricing_error,
    }


BenchmarkFetcher = Callable[
    [httpx.AsyncClient, str, int],
    Awaitable[tuple[object, str | None]],
]

_BENCHMARK_FETCHERS: dict[str, BenchmarkFetcher] = {
    "design_arena": fetch_design_arena,
    "artificial_analysis": fetch_artificial_analysis,
    "benchmark_scores": fetch_benchmark_scores,
    "effective_pricing": fetch_effective_pricing,
}


async def _refetch_benchmark_failures(
    client: httpx.AsyncClient,
    records: list[dict[str, object]],
    retries: int,
) -> int:
    """Slow second attempt at benchmark sources that failed the first pass.

    The private frontend endpoints throttle a full-catalog crawl, so retrying
    the failures gently (low concurrency, spaced out) recovers most of what the
    first pass lost to 429s.
    """
    pending: list[tuple[dict[str, object], str, str]] = []
    for record in records:
        slug = record.get("canonical_slug")
        if not isinstance(slug, str):
            continue
        for source in BENCHMARK_SOURCES:
            if record.get(f"{source}_error") is not None:
                pending.append((record, slug, source))
    if not pending:
        return 0
    semaphore = asyncio.Semaphore(RETRY_PASS_CONCURRENCY)

    async def retry(
        record: dict[str, object],
        slug: str,
        source: str,
    ) -> tuple[dict[str, object], str, object, str | None]:
        async with semaphore:
            await asyncio.sleep(RETRY_PASS_SPACING_SECONDS)
            data, error = await _BENCHMARK_FETCHERS[source](client, slug, retries)
        return record, source, data, error

    recovered = 0
    for record, source, data, error in await asyncio.gather(
        *(retry(record, slug, source) for record, slug, source in pending)
    ):
        if error is None:
            record[source] = data
            record[f"{source}_error"] = None
            recovered += 1
    return recovered


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
    headers = auth_headers(api_key)
    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        tasks = [
            _fetch_model_benchmarks(client, canonical_slug, retries, semaphore)
            for canonical_slug in canonical_slugs
        ]
        results = list(await asyncio.gather(*tasks))
        await _refetch_benchmark_failures(client, results, retries)
        return results


async def fetch_models_async(
    options: FetchOptions | None = None,
) -> list[dict[str, object]]:
    opts = options or {}
    api_key = opts.get("api_key") or os.environ.get("OPENROUTER_API_KEY")
    timeout_seconds = opts.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    headers = auth_headers(api_key)
    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        return await fetch_models(client)
