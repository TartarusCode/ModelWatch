import asyncio
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest

from modelwatch import fetch


def test_benchmark_urls_use_frontend_private_api() -> None:
    assert "frontend/v1/private" in fetch.DESIGN_ARENA_URL
    assert "frontend/v1/private" in fetch.ARTIFICIAL_ANALYSIS_URL
    assert "internal/v1" not in fetch.DESIGN_ARENA_URL
    assert "internal/v1" not in fetch.ARTIFICIAL_ANALYSIS_URL


def test_slug_stats_urls_use_frontend_stats_api() -> None:
    slug = "minimax/minimax-m2.7-20260318"
    scores_url = fetch.benchmark_scores_url(slug)
    pricing_url = fetch.effective_pricing_url(slug)
    assert "frontend/v1/stats/benchmark-scores" in scores_url
    assert "permaslug=minimax%2Fminimax-m2.7-20260318" in scores_url
    assert "frontend/v1/stats/effective-pricing" in pricing_url
    assert "variant=standard" in pricing_url


def test_endpoints_url_for_model_id_handles_free_variant() -> None:
    url = fetch.endpoints_url_for_model_id("meta-llama/llama-3.3-70b-instruct:free")
    assert (
        url
        == "https://openrouter.ai/api/v1/models/meta-llama/llama-3.3-70b-instruct%3Afree/endpoints"
    )


def test_fetch_benchmark_scores_parses_scores() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "benchmark-scores" in str(request.url)
        return httpx.Response(
            200,
            json={
                "data": {
                    "scores": [
                        {
                            "provider_name": "DeepInfra",
                            "benchmark_type": "gpqa_diamond",
                            "score": 0.85,
                            "run_count": 6,
                        }
                    ]
                }
            },
        )

    transport = httpx.MockTransport(handler)

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            data, error = await fetch.fetch_benchmark_scores(
                client,
                "minimax/minimax-m2.7-20260318",
                retries=0,
            )
        assert error is None
        assert isinstance(data, dict)
        scores = data.get("scores")
        assert isinstance(scores, list)
        assert len(scores) == 1

    asyncio.run(run())


def test_fetch_provider_endpoints_parses_endpoints() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/deepseek/deepseek-chat/endpoints")
        return httpx.Response(
            200,
            json={
                "data": {
                    "endpoints": [
                        {
                            "provider_name": "DeepInfra",
                            "name": "DeepInfra | demo",
                            "pricing": {"prompt": "0.1", "completion": "0.2"},
                        }
                    ]
                }
            },
        )

    transport = httpx.MockTransport(handler)

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            data, error = await fetch.fetch_provider_endpoints(
                client,
                "deepseek/deepseek-chat",
                retries=0,
            )
        assert error is None
        assert isinstance(data, dict)
        endpoints = data.get("endpoints")
        assert isinstance(endpoints, list)
        assert len(endpoints) == 1

    asyncio.run(run())


def test_throttled_response_is_retried_even_without_a_retry_budget() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"data": {"ok": True}})

    transport = httpx.MockTransport(handler)

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            payload = await fetch._fetch_json_with_retries(
                client,
                "https://openrouter.ai/api/frontend/v1/private/x",
                retries=0,
            )
        assert payload == {"data": {"ok": True}}

    asyncio.run(run())
    assert len(calls) == 2


def test_non_retryable_status_is_not_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(404, json={"error": "missing"})

    transport = httpx.MockTransport(handler)

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await fetch._fetch_json_with_retries(
                    client,
                    "https://openrouter.ai/api/frontend/v1/private/x",
                    retries=2,
                )

    asyncio.run(run())
    assert len(calls) == 1


def test_retry_delay_prefers_retry_after_header() -> None:
    response = httpx.Response(429, headers={"Retry-After": "3"})
    assert fetch._retry_delay_seconds(response, attempt=0) == 3.0

    capped = httpx.Response(429, headers={"Retry-After": "999"})
    assert (
        fetch._retry_delay_seconds(capped, attempt=0) == fetch.MAX_RETRY_DELAY_SECONDS
    )

    when = datetime.now(UTC) + timedelta(seconds=4)
    dated = httpx.Response(429, headers={"Retry-After": format_datetime(when)})
    delay = fetch._retry_delay_seconds(dated, attempt=0)
    assert 2.0 < delay <= 4.0


def test_retry_delay_falls_back_to_backoff_with_jitter() -> None:
    for attempt in range(4):
        delay = fetch._retry_delay_seconds(None, attempt)
        base = min(2.0**attempt, 8.0)
        assert base <= delay < base * 1.5


def test_refetch_benchmark_failures_recovers_errored_sources() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "artificial-analysis" in str(request.url):
            return httpx.Response(200, json={"data": [{"eval": "x"}]})
        return httpx.Response(200, json={"data": {"ok": True}})

    transport = httpx.MockTransport(handler)
    records: list[dict[str, object]] = [
        {
            "canonical_slug": "deepseek/deepseek-v4.1-flash",
            "design_arena": None,
            "design_arena_error": "429 Too Many Requests",
            "artificial_analysis": None,
            "artificial_analysis_error": "429 Too Many Requests",
            "benchmark_scores": {"scores": []},
            "benchmark_scores_error": None,
            "effective_pricing": {"ok": True},
            "effective_pricing_error": None,
        }
    ]

    async def run() -> int:
        async with httpx.AsyncClient(transport=transport) as client:
            return await fetch._refetch_benchmark_failures(
                client,
                records,
                retries=0,
            )

    recovered = asyncio.run(run())

    assert recovered == 2
    assert records[0]["design_arena"] == {"ok": True}
    assert records[0]["design_arena_error"] is None
    assert records[0]["artificial_analysis"] == [{"eval": "x"}]
    assert records[0]["artificial_analysis_error"] is None
    # only the failed sources were fetched again
    assert len(seen) == 2
    assert all("benchmark-scores" not in url for url in seen)


def test_refetch_benchmark_failures_is_a_no_op_without_failures() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no request expected")

    transport = httpx.MockTransport(handler)
    records: list[dict[str, object]] = [
        {
            "canonical_slug": "deepseek/deepseek-v4.1-flash",
            "design_arena": {"ok": True},
            "design_arena_error": None,
            "artificial_analysis": [],
            "artificial_analysis_error": None,
            "benchmark_scores": {"scores": []},
            "benchmark_scores_error": None,
            "effective_pricing": {"ok": True},
            "effective_pricing_error": None,
        }
    ]

    async def run() -> int:
        async with httpx.AsyncClient(transport=transport) as client:
            return await fetch._refetch_benchmark_failures(
                client,
                records,
                retries=0,
            )

    assert asyncio.run(run()) == 0
