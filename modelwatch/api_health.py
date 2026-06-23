import asyncio
import os
import sys
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from modelwatch.benchmark_health import (
    PROBE_SLUGS,
    ProbeResult,
    endpoint_is_healthy,
    probes_indicate_broken_endpoints,
)
from modelwatch.fetch import (
    ARTIFICIAL_ANALYSIS_URL,
    DESIGN_ARENA_URL,
    MODELS_URL,
    _auth_headers,
)

PROBE_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class ApiHealthReport:
    models_ok: bool
    results: list[ProbeResult]
    broken: bool


async def _probe_url(
    client: httpx.AsyncClient,
    *,
    endpoint: str,
    base_url: str,
    slug: str,
) -> ProbeResult:
    url = f"{base_url}?slug={quote(slug, safe='')}"
    try:
        response = await client.get(url)
        payload: dict[str, object] = {}
        if response.headers.get("content-type", "").startswith("application/json"):
            json_payload = response.json()
            if isinstance(json_payload, dict):
                payload = json_payload
        ok = endpoint_is_healthy(response.status_code, payload)
        return ProbeResult(
            endpoint=endpoint,
            slug=slug,
            status_code=response.status_code,
            ok=ok,
        )
    except Exception:
        return ProbeResult(endpoint=endpoint, slug=slug, status_code=0, ok=False)


async def _probe_models(client: httpx.AsyncClient) -> bool:
    try:
        response = await client.get(MODELS_URL)
        if response.status_code != 200:
            return False
        payload = response.json()
        if not isinstance(payload, dict):
            return False
        data = payload.get("data")
        return isinstance(data, list) and len(data) > 0
    except Exception:
        return False


async def probe_benchmark_endpoints(
    *,
    client: httpx.AsyncClient,
    slugs: list[str] | None = None,
) -> ApiHealthReport:
    probe_slugs = slugs if slugs is not None else PROBE_SLUGS
    results: list[ProbeResult] = []
    for slug in probe_slugs:
        design_result = await _probe_url(
            client,
            endpoint="design_arena",
            base_url=DESIGN_ARENA_URL,
            slug=slug,
        )
        aa_result = await _probe_url(
            client,
            endpoint="artificial_analysis",
            base_url=ARTIFICIAL_ANALYSIS_URL,
            slug=slug,
        )
        results.extend([design_result, aa_result])

    models_ok = await _probe_models(client)
    broken = probes_indicate_broken_endpoints(results)
    return ApiHealthReport(models_ok=models_ok, results=results, broken=broken)


def format_report(report: ApiHealthReport) -> str:
    lines = [
        f"models_api_ok={report.models_ok}",
        f"benchmark_probes_broken={report.broken}",
    ]
    for result in report.results:
        status = "ok" if result.ok else "fail"
        lines.append(
            f"  {result.endpoint} slug={result.slug} "
            f"status={result.status_code} {status}"
        )
    return "\n".join(lines)


async def run_api_health() -> ApiHealthReport:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    headers = _auth_headers(api_key)
    timeout = httpx.Timeout(PROBE_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        return await probe_benchmark_endpoints(client=client)


def main() -> None:
    report = asyncio.run(run_api_health())
    print(format_report(report))
    if not report.models_ok:
        print("Models API probe failed", file=sys.stderr)
        raise SystemExit(1)
    if report.broken:
        print(
            "All benchmark endpoint probes failed — URLs may be stale",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
