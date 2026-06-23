from modelwatch.discover_benchmark_urls import (
    BENCHMARK_URL_MARKERS,
    DISCOVER_PAGES,
    discovery_matches_config,
    format_discovery_mismatch,
    normalize_benchmark_endpoint_url,
)


def test_normalize_benchmark_endpoint_url_strips_query() -> None:
    url = (
        "https://openrouter.ai/api/frontend/v1/private/"
        "design-arena-benchmarks?slug=cohere%2Fnorth-mini-code"
    )
    assert normalize_benchmark_endpoint_url(url) == (
        "https://openrouter.ai/api/frontend/v1/private/design-arena-benchmarks"
    )


def test_normalize_returns_none_for_unrelated_url() -> None:
    assert normalize_benchmark_endpoint_url("https://openrouter.ai/api/v1/models") is None


def test_discovery_matches_config_when_urls_match() -> None:
    design = "https://openrouter.ai/api/frontend/v1/private/design-arena-benchmarks"
    aa = "https://openrouter.ai/api/frontend/v1/private/artificial-analysis-benchmarks"
    discovered = {design, aa}
    assert discovery_matches_config(discovered, design_url=design, aa_url=aa) is True


def test_discovery_matches_config_false_on_mismatch() -> None:
    design = "https://openrouter.ai/api/frontend/v1/private/design-arena-benchmarks"
    aa = "https://openrouter.ai/api/frontend/v1/private/artificial-analysis-benchmarks"
    discovered = {
        "https://openrouter.ai/api/internal/v1/design-arena-benchmarks",
        "https://openrouter.ai/api/internal/v1/artificial-analysis-benchmarks",
    }
    assert discovery_matches_config(discovered, design_url=design, aa_url=aa) is False


def test_format_discovery_mismatch_includes_suggested_urls() -> None:
    message = format_discovery_mismatch(
        discovered={"https://openrouter.ai/api/new/design-arena-benchmarks"},
        design_url="https://openrouter.ai/api/old/design-arena-benchmarks",
        aa_url="https://openrouter.ai/api/old/artificial-analysis-benchmarks",
    )
    assert "design-arena-benchmarks" in message
    assert "fetch.py" in message


def test_discover_pages_and_markers_configured() -> None:
    assert len(DISCOVER_PAGES) >= 2
    assert "design-arena-benchmarks" in BENCHMARK_URL_MARKERS
    assert "artificial-analysis-benchmarks" in BENCHMARK_URL_MARKERS
