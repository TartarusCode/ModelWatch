from modelwatch import fetch


def test_benchmark_urls_use_frontend_private_api() -> None:
    assert "frontend/v1/private" in fetch.DESIGN_ARENA_URL
    assert "frontend/v1/private" in fetch.ARTIFICIAL_ANALYSIS_URL
    assert "internal/v1" not in fetch.DESIGN_ARENA_URL
    assert "internal/v1" not in fetch.ARTIFICIAL_ANALYSIS_URL
