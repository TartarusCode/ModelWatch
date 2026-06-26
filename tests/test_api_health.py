import asyncio

import httpx

from modelwatch.api_health import ApiHealthReport, probe_benchmark_endpoints
from modelwatch.benchmark_health import PROBE_SLUGS
from modelwatch.fetch import MODELS_URL


def _mock_transport(
    *,
    design_status: int = 200,
    aa_status: int = 200,
    models_status: int = 200,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == MODELS_URL:
            return httpx.Response(
                models_status,
                json={"data": [{"id": "test/model"}]},
            )
        if request.url.host and "design-arena-benchmarks" in str(request.url):
            return httpx.Response(
                design_status,
                json={"data": {"records": [], "eloBounds": {"min": 0, "max": 1}}},
            )
        if request.url.host and "artificial-analysis-benchmarks" in str(request.url):
            return httpx.Response(aa_status, json={"data": []})
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


async def _probe(
    *,
    design_status: int = 200,
    aa_status: int = 200,
    models_status: int = 200,
) -> ApiHealthReport:
    async with httpx.AsyncClient(
        transport=_mock_transport(
            design_status=design_status,
            aa_status=aa_status,
            models_status=models_status,
        ),
    ) as client:
        return await probe_benchmark_endpoints(client=client, slugs=["a/b"])


def test_probe_benchmark_endpoints_all_healthy() -> None:
    report = asyncio.run(_probe())
    assert report.models_ok is True
    assert report.broken is False
    assert all(result.ok for result in report.results)


def test_probe_benchmark_endpoints_broken_when_all_404() -> None:
    report = asyncio.run(_probe(design_status=404, aa_status=404, models_status=200))
    assert report.broken is True
    assert not any(result.ok for result in report.results)


def test_probe_uses_default_slugs_when_none_provided() -> None:
    requested_slugs: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "slug=" in str(request.url):
            slug = str(request.url).split("slug=", 1)[1]
            requested_slugs.append(slug)
            return httpx.Response(200, json={"data": []})
        return httpx.Response(200, json={"data": []})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await probe_benchmark_endpoints(client=client)

    asyncio.run(run())

    for slug in PROBE_SLUGS:
        assert slug.replace("/", "%2F") in requested_slugs
