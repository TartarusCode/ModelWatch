import re
from dataclasses import dataclass

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


@dataclass(frozen=True)
class MergedProviderRow:
    provider_name: str
    provider_key: str
    list_prompt: str | None
    list_completion: str | None
    effective_input_price: float | None
    effective_output_price: float | None
    cache_hit_rate: float | None
    uptime_last_30m: float | None


def normalize_provider_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower())


def parse_benchmark_scores_payload(
    raw: dict[str, object],
) -> list[BenchmarkScoreRecord]:
    scores = raw.get("scores")
    if not isinstance(scores, list):
        return []
    records: list[BenchmarkScoreRecord] = []
    for item in scores:
        if not isinstance(item, dict):
            continue
        provider_name = item.get("provider_name")
        benchmark_type = item.get("benchmark_type")
        score = item.get("score")
        run_count = item.get("run_count")
        if (
            not isinstance(provider_name, str)
            or not isinstance(benchmark_type, str)
            or not isinstance(score, (int, float))
            or not isinstance(run_count, (int, float))
        ):
            continue
        records.append(
            BenchmarkScoreRecord(
                provider_name=provider_name,
                benchmark_type=benchmark_type,
                score=float(score),
                run_count=int(run_count),
            )
        )
    return records


def parse_effective_pricing_payload(
    raw: dict[str, object],
) -> EffectivePricing | None:
    summaries_raw = raw.get("providerSummaries")
    summaries: list[EffectivePricingProviderSummary] = []
    if isinstance(summaries_raw, list):
        for item in summaries_raw:
            if not isinstance(item, dict):
                continue
            provider_name = item.get("providerName")
            provider_slug = item.get("providerSlug")
            input_price = item.get("effectiveInputPrice")
            output_price = item.get("effectiveOutputPrice")
            cache_hit_rate = item.get("cacheHitRate")
            total_tokens = item.get("totalTokens")
            if (
                not isinstance(provider_name, str)
                or not isinstance(provider_slug, str)
                or not isinstance(input_price, (int, float))
                or not isinstance(output_price, (int, float))
                or not isinstance(cache_hit_rate, (int, float))
                or not isinstance(total_tokens, (int, float))
            ):
                continue
            summaries.append(
                EffectivePricingProviderSummary(
                    provider_name=provider_name,
                    provider_slug=provider_slug,
                    effective_input_price=float(input_price),
                    effective_output_price=float(output_price),
                    cache_hit_rate=float(cache_hit_rate),
                    total_tokens=int(total_tokens),
                )
            )
    weighted_input = raw.get("weightedInputPrice")
    weighted_output = raw.get("weightedOutputPrice")
    weighted_cache = raw.get("weightedCacheHitRate")
    if not summaries and not any(
        isinstance(value, (int, float))
        for value in (weighted_input, weighted_output, weighted_cache)
    ):
        return None
    return EffectivePricing(
        weighted_input_price=float(weighted_input)
        if isinstance(weighted_input, (int, float))
        else None,
        weighted_output_price=float(weighted_output)
        if isinstance(weighted_output, (int, float))
        else None,
        weighted_cache_hit_rate=float(weighted_cache)
        if isinstance(weighted_cache, (int, float))
        else None,
        provider_summaries=summaries,
    )


def parse_provider_endpoints_payload(
    raw: dict[str, object],
) -> list[ProviderEndpoint]:
    endpoints_raw = raw.get("endpoints")
    if not isinstance(endpoints_raw, list):
        return []
    endpoints: list[ProviderEndpoint] = []
    for item in endpoints_raw:
        if not isinstance(item, dict):
            continue
        provider_name = item.get("provider_name")
        name = item.get("name")
        pricing_raw = item.get("pricing")
        if (
            not isinstance(provider_name, str)
            or not isinstance(name, str)
            or not isinstance(pricing_raw, dict)
        ):
            continue
        prompt = pricing_raw.get("prompt")
        completion = pricing_raw.get("completion")
        if not isinstance(prompt, str) or not isinstance(completion, str):
            continue
        uptime = item.get("uptime_last_30m")
        context_length = item.get("context_length")
        endpoints.append(
            ProviderEndpoint(
                provider_name=provider_name,
                name=name,
                pricing=ProviderEndpointPricing(
                    prompt=prompt,
                    completion=completion,
                ),
                uptime_last_30m=float(uptime)
                if isinstance(uptime, (int, float))
                else None,
                context_length=int(context_length)
                if isinstance(context_length, (int, float))
                else None,
            )
        )
    return endpoints


def _status_from_fetch(
    *,
    error: str | None,
    has_data: bool,
) -> BenchmarkFetchStatus:
    if error is not None:
        return BenchmarkFetchStatus(status="error", error=error)
    if has_data:
        return BenchmarkFetchStatus(status="ok")
    return BenchmarkFetchStatus(status="empty")


def build_benchmark_scores(
    raw: dict[str, object] | None,
    *,
    error: str | None,
) -> tuple[list[BenchmarkScoreRecord] | None, BenchmarkFetchStatus]:
    if error is not None:
        return None, BenchmarkFetchStatus(status="error", error=error)
    if not isinstance(raw, dict):
        return None, BenchmarkFetchStatus(status="empty")
    records = parse_benchmark_scores_payload(raw)
    status = _status_from_fetch(error=None, has_data=len(records) > 0)
    return (records if records else None), status


def build_provider_stats(
    *,
    effective_pricing_raw: dict[str, object] | None,
    effective_pricing_error: str | None,
    endpoints_raw: dict[str, object] | None,
    endpoints_error: str | None,
) -> ModelProviderStats:
    effective_pricing: EffectivePricing | None = None
    if effective_pricing_error is not None:
        effective_status = BenchmarkFetchStatus(
            status="error",
            error=effective_pricing_error,
        )
    elif isinstance(effective_pricing_raw, dict):
        effective_pricing = parse_effective_pricing_payload(effective_pricing_raw)
        effective_status = _status_from_fetch(
            error=None,
            has_data=effective_pricing is not None,
        )
    else:
        effective_status = BenchmarkFetchStatus(status="empty")

    endpoints: list[ProviderEndpoint] = []
    if endpoints_error is not None:
        endpoints_status = BenchmarkFetchStatus(status="error", error=endpoints_error)
    elif isinstance(endpoints_raw, dict):
        endpoints = parse_provider_endpoints_payload(endpoints_raw)
        endpoints_status = _status_from_fetch(error=None, has_data=len(endpoints) > 0)
    else:
        endpoints_status = BenchmarkFetchStatus(status="empty")

    return ModelProviderStats(
        effective_pricing=effective_pricing,
        effective_pricing_status=effective_status,
        provider_endpoints=endpoints,
        provider_endpoints_status=endpoints_status,
    )


def merge_provider_rows(
    effective_pricing: EffectivePricing | None,
    endpoints: list[ProviderEndpoint],
) -> list[MergedProviderRow]:
    rows_by_key: dict[str, MergedProviderRow] = {}

    if effective_pricing is not None:
        for summary in effective_pricing.provider_summaries:
            key = normalize_provider_key(summary.provider_slug)
            rows_by_key[key] = MergedProviderRow(
                provider_name=summary.provider_name,
                provider_key=key,
                list_prompt=None,
                list_completion=None,
                effective_input_price=summary.effective_input_price,
                effective_output_price=summary.effective_output_price,
                cache_hit_rate=summary.cache_hit_rate,
                uptime_last_30m=None,
            )

    for endpoint in endpoints:
        key = normalize_provider_key(endpoint.provider_name)
        existing = rows_by_key.get(key)
        if existing is None:
            rows_by_key[key] = MergedProviderRow(
                provider_name=endpoint.provider_name,
                provider_key=key,
                list_prompt=endpoint.pricing.prompt,
                list_completion=endpoint.pricing.completion,
                effective_input_price=None,
                effective_output_price=None,
                cache_hit_rate=None,
                uptime_last_30m=endpoint.uptime_last_30m,
            )
            continue
        rows_by_key[key] = MergedProviderRow(
            provider_name=existing.provider_name,
            provider_key=existing.provider_key,
            list_prompt=endpoint.pricing.prompt,
            list_completion=endpoint.pricing.completion,
            effective_input_price=existing.effective_input_price,
            effective_output_price=existing.effective_output_price,
            cache_hit_rate=existing.cache_hit_rate,
            uptime_last_30m=endpoint.uptime_last_30m,
        )

    return sorted(rows_by_key.values(), key=lambda row: row.provider_name.lower())


def stabilize_provider_stats(
    stats: ModelProviderStats,
    benchmarks: ModelBenchmarks,
) -> tuple[ModelProviderStats, ModelBenchmarks]:
    stabilized_effective = stats.effective_pricing
    if stabilized_effective is not None:
        stabilized_effective = stabilized_effective.model_copy(
            update={
                "provider_summaries": sorted(
                    stabilized_effective.provider_summaries,
                    key=lambda summary: (-summary.total_tokens, summary.provider_name),
                ),
            },
        )
    stabilized_endpoints = sorted(
        stats.provider_endpoints,
        key=lambda endpoint: (endpoint.provider_name.lower(), endpoint.name.lower()),
    )
    stabilized_stats = stats.model_copy(
        update={
            "effective_pricing": stabilized_effective,
            "provider_endpoints": stabilized_endpoints,
        },
    )
    return stabilized_stats, benchmarks
