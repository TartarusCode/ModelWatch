from modelwatch.provider_stats import (
    build_provider_stats,
    merge_provider_rows,
    normalize_provider_key,
    parse_benchmark_scores_payload,
    parse_effective_pricing_payload,
    parse_provider_endpoints_payload,
    stabilize_provider_stats,
)
from modelwatch.schemas import (
    BenchmarkFetchStatus,
    BenchmarkScoreRecord,
    EffectivePricing,
    EffectivePricingProviderSummary,
    ModelBenchmarks,
    ModelProviderStats,
    ProviderEndpoint,
    ProviderEndpointPricing,
)


def test_normalize_provider_key_matches_slug_and_name() -> None:
    assert normalize_provider_key("DeepInfra") == "deepinfra"
    assert normalize_provider_key("deepinfra") == "deepinfra"
    assert normalize_provider_key("MiniMax Highspeed") == "minimax highspeed"


def test_parse_benchmark_scores_payload_trims_fields() -> None:
    raw = {
        "scores": [
            {
                "provider_name": "DeepInfra",
                "benchmark_type": "gpqa_diamond",
                "score": 0.8543088746349657,
                "run_count": 6,
                "extra": "ignored",
            }
        ],
        "lookback_days": 32,
    }
    records = parse_benchmark_scores_payload(raw)
    assert records == [
        BenchmarkScoreRecord(
            provider_name="DeepInfra",
            benchmark_type="gpqa_diamond",
            score=0.8543088746349657,
            run_count=6,
        )
    ]


def test_parse_effective_pricing_payload_trims_summaries() -> None:
    raw = {
        "weightedInputPrice": 0.131,
        "weightedOutputPrice": 1.192,
        "weightedCacheHitRate": 0.713,
        "providerSummaries": [
            {
                "providerName": "MiniMax",
                "providerSlug": "minimax",
                "effectiveInputPrice": 0.117,
                "effectiveOutputPrice": 1.199,
                "cacheHitRate": 0.761,
                "totalTokens": 271000502,
            }
        ],
        "inputChartData": [{"x": "2026-06-26", "y": {}}],
    }
    parsed = parse_effective_pricing_payload(raw)
    assert parsed == EffectivePricing(
        weighted_input_price=0.131,
        weighted_output_price=1.192,
        weighted_cache_hit_rate=0.713,
        provider_summaries=[
            EffectivePricingProviderSummary(
                provider_name="MiniMax",
                provider_slug="minimax",
                effective_input_price=0.117,
                effective_output_price=1.199,
                cache_hit_rate=0.761,
                total_tokens=271000502,
            )
        ],
    )


def test_parse_provider_endpoints_payload_trims_fields() -> None:
    raw = {
        "endpoints": [
            {
                "provider_name": "DeepInfra",
                "name": "DeepInfra | deepseek/deepseek-chat-v3",
                "pricing": {"prompt": "0.00000014", "completion": "0.00000028"},
                "uptime_last_30m": 0.999,
                "context_length": 163840,
                "supported_parameters": ["temperature"],
            }
        ]
    }
    endpoints = parse_provider_endpoints_payload(raw)
    assert endpoints == [
        ProviderEndpoint(
            provider_name="DeepInfra",
            name="DeepInfra | deepseek/deepseek-chat-v3",
            pricing=ProviderEndpointPricing(
                prompt="0.00000014",
                completion="0.00000028",
            ),
            uptime_last_30m=0.999,
            context_length=163840,
        )
    ]


def test_build_provider_stats_maps_fetch_results() -> None:
    stats = build_provider_stats(
        effective_pricing_raw={
            "weightedInputPrice": 0.1,
            "weightedOutputPrice": 1.0,
            "weightedCacheHitRate": 0.5,
            "providerSummaries": [],
        },
        effective_pricing_error=None,
        endpoints_raw={"endpoints": []},
        endpoints_error=None,
    )
    assert stats.effective_pricing_status.status == "ok"
    assert stats.provider_endpoints_status.status == "empty"


def test_merge_provider_rows_joins_by_provider_key() -> None:
    effective = EffectivePricing(
        weighted_input_price=0.1,
        weighted_output_price=1.0,
        weighted_cache_hit_rate=0.5,
        provider_summaries=[
            EffectivePricingProviderSummary(
                provider_name="DeepInfra",
                provider_slug="deepinfra",
                effective_input_price=0.09,
                effective_output_price=0.95,
                cache_hit_rate=0.81,
                total_tokens=1000,
            )
        ],
    )
    endpoints = [
        ProviderEndpoint(
            provider_name="DeepInfra",
            name="DeepInfra | model",
            pricing=ProviderEndpointPricing(
                prompt="0.0000001",
                completion="0.0000002",
            ),
            uptime_last_30m=0.99,
            context_length=None,
        )
    ]
    rows = merge_provider_rows(effective, endpoints)
    assert len(rows) == 1
    assert rows[0].provider_name == "DeepInfra"
    assert rows[0].list_prompt == "0.0000001"
    assert rows[0].effective_input_price == 0.09
    assert rows[0].cache_hit_rate == 0.81
    assert rows[0].uptime_last_30m == 0.99


def test_stabilize_provider_stats_sorts_summaries_and_endpoints() -> None:
    stats = ModelProviderStats(
        effective_pricing=EffectivePricing(
            weighted_input_price=0.1,
            weighted_output_price=1.0,
            weighted_cache_hit_rate=0.5,
            provider_summaries=[
                EffectivePricingProviderSummary(
                    provider_name="B",
                    provider_slug="b",
                    effective_input_price=0.1,
                    effective_output_price=1.0,
                    cache_hit_rate=0.5,
                    total_tokens=100,
                ),
                EffectivePricingProviderSummary(
                    provider_name="A",
                    provider_slug="a",
                    effective_input_price=0.1,
                    effective_output_price=1.0,
                    cache_hit_rate=0.5,
                    total_tokens=200,
                ),
            ],
        ),
        effective_pricing_status=BenchmarkFetchStatus(status="ok"),
        provider_endpoints=[
            ProviderEndpoint(
                provider_name="Z",
                name="z",
                pricing=ProviderEndpointPricing(prompt="0.1", completion="0.2"),
                uptime_last_30m=None,
                context_length=None,
            ),
            ProviderEndpoint(
                provider_name="A",
                name="a",
                pricing=ProviderEndpointPricing(prompt="0.1", completion="0.2"),
                uptime_last_30m=None,
                context_length=None,
            ),
        ],
        provider_endpoints_status=BenchmarkFetchStatus(status="ok"),
    )
    benchmarks = ModelBenchmarks(
        design_arena_status=BenchmarkFetchStatus(status="empty"),
        artificial_analysis=[],
        artificial_analysis_status=BenchmarkFetchStatus(status="empty"),
        benchmark_scores=[
            BenchmarkScoreRecord(
                provider_name="Z",
                benchmark_type="gpqa_diamond",
                score=0.5,
                run_count=1,
            ),
            BenchmarkScoreRecord(
                provider_name="A",
                benchmark_type="gpqa_diamond",
                score=0.6,
                run_count=2,
            ),
        ],
        benchmark_scores_status=BenchmarkFetchStatus(status="ok"),
    )
    stabilized_stats, stabilized_benchmarks = stabilize_provider_stats(
        stats,
        benchmarks,
    )
    assert [
        summary.provider_name
        for summary in stabilized_stats.effective_pricing.provider_summaries  # type: ignore[union-attr]
    ] == ["A", "B"]
    assert [endpoint.provider_name for endpoint in stabilized_stats.provider_endpoints] == [
        "A",
        "Z",
    ]
    assert [
        record.provider_name for record in stabilized_benchmarks.benchmark_scores or []
    ] == ["A", "Z"]
