import asyncio

import httpx

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
