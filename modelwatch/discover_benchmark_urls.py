import sys
from urllib.parse import urlsplit, urlunsplit

from modelwatch.fetch import ARTIFICIAL_ANALYSIS_URL, DESIGN_ARENA_URL

DISCOVER_PAGES = [
    "https://openrouter.ai/moonshotai/kimi-k2.7-code",
    (
        "https://openrouter.ai/compare/deepseek/deepseek-v4-flash/"
        "tencent/hy3-preview/google/gemini-2.5-flash-lite"
    ),
]

BENCHMARK_URL_MARKERS = (
    "design-arena-benchmarks",
    "artificial-analysis-benchmarks",
)

DISCOVERY_TIMEOUT_MS = 60_000


def normalize_benchmark_endpoint_url(url: str) -> str | None:
    if not any(marker in url for marker in BENCHMARK_URL_MARKERS):
        return None
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def discovery_matches_config(
    discovered: set[str],
    *,
    design_url: str,
    aa_url: str,
) -> bool:
    return design_url in discovered and aa_url in discovered


def format_discovery_mismatch(
    *,
    discovered: set[str],
    design_url: str,
    aa_url: str,
) -> str:
    lines = [
        "Benchmark URL discovery mismatch — update modelwatch/fetch.py:",
        f"  discovered: {sorted(discovered)}",
        f"  configured design_arena: {design_url}",
        f"  configured artificial_analysis: {aa_url}",
    ]
    design_candidates = sorted(
        url for url in discovered if "design-arena-benchmarks" in url
    )
    aa_candidates = sorted(
        url for url in discovered if "artificial-analysis-benchmarks" in url
    )
    if design_candidates:
        lines.append(f'  DESIGN_ARENA_URL = "{design_candidates[0]}"')
    if aa_candidates:
        lines.append(f'  ARTIFICIAL_ANALYSIS_URL = "{aa_candidates[0]}"')
    return "\n".join(lines)


async def discover_benchmark_urls_from_pages(
    pages: list[str],
) -> set[str]:
    from playwright.async_api import async_playwright

    discovered: set[str] = set()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()

            def on_request(request: object) -> None:
                url = getattr(request, "url", "")
                if not isinstance(url, str):
                    return
                normalized = normalize_benchmark_endpoint_url(url)
                if normalized is not None:
                    discovered.add(normalized)

            page.on("request", on_request)
            for page_url in pages:
                await page.goto(page_url, wait_until="networkidle", timeout=DISCOVERY_TIMEOUT_MS)
        finally:
            await browser.close()

    return discovered


async def run_discovery() -> int:
    discovered = await discover_benchmark_urls_from_pages(DISCOVER_PAGES)
    if not discovered:
        print(
            "No benchmark URLs discovered from OpenRouter pages",
            file=sys.stderr,
        )
        return 1

    if discovery_matches_config(
        discovered,
        design_url=DESIGN_ARENA_URL,
        aa_url=ARTIFICIAL_ANALYSIS_URL,
    ):
        print(f"Benchmark URLs match fetch.py ({len(discovered)} endpoints seen)")
        return 0

    print(
        format_discovery_mismatch(
            discovered=discovered,
            design_url=DESIGN_ARENA_URL,
            aa_url=ARTIFICIAL_ANALYSIS_URL,
        ),
        file=sys.stderr,
    )
    return 1


def main() -> None:
    import asyncio

    raise SystemExit(asyncio.run(run_discovery()))


if __name__ == "__main__":
    main()
