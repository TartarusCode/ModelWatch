from modelwatch.build import _build_benchmarks
from modelwatch.provider_stats import build_provider_stats


def test_build_benchmarks_includes_benchmark_scores_status() -> None:
    benchmarks = _build_benchmarks(
        {
            "benchmark_scores": {
                "scores": [
                    {
                        "provider_name": "DeepInfra",
                        "benchmark_type": "gpqa_diamond",
                        "score": 0.85,
                        "run_count": 4,
                    }
                ]
            },
            "benchmark_scores_error": None,
            "design_arena_error": "fail",
            "artificial_analysis_error": "fail",
        }
    )
    assert benchmarks.benchmark_scores_status.status == "ok"
    assert benchmarks.benchmark_scores is not None
    assert len(benchmarks.benchmark_scores) == 1


def test_build_provider_stats_from_fetch_payload() -> None:
    stats = build_provider_stats(
        effective_pricing_raw={
            "weightedInputPrice": 0.1,
            "weightedOutputPrice": 1.0,
            "weightedCacheHitRate": 0.5,
            "providerSummaries": [
                {
                    "providerName": "DeepInfra",
                    "providerSlug": "deepinfra",
                    "effectiveInputPrice": 0.09,
                    "effectiveOutputPrice": 0.95,
                    "cacheHitRate": 0.8,
                    "totalTokens": 1000,
                }
            ],
        },
        effective_pricing_error=None,
        endpoints_raw={
            "endpoints": [
                {
                    "provider_name": "DeepInfra",
                    "name": "DeepInfra | demo",
                    "pricing": {"prompt": "0.1", "completion": "0.2"},
                    "uptime_last_30m": 0.99,
                }
            ]
        },
        endpoints_error=None,
    )
    assert stats.effective_pricing_status.status == "ok"
    assert stats.provider_endpoints_status.status == "ok"
    assert len(stats.provider_endpoints) == 1
