from dataclasses import dataclass

PROBE_SLUGS = [
    "anthropic/claude-4.6-sonnet-20260217",
    "google/gemini-2.5-flash-lite",
    "moonshotai/kimi-k2.7-code",
]

MAX_BENCHMARK_ERROR_RATIO = 0.5


class BenchmarkHealthError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProbeResult:
    endpoint: str
    slug: str
    status_code: int
    ok: bool


def endpoint_is_healthy(status_code: int, payload: dict[str, object]) -> bool:
    if status_code != 200:
        return False
    return "data" in payload


def probes_indicate_broken_endpoints(results: list[ProbeResult]) -> bool:
    if not results:
        return True
    return not any(result.ok for result in results)


def benchmark_error_ratio(benchmark_errors: int, model_count: int) -> float:
    if model_count <= 0:
        return 0.0
    total_endpoints = model_count * 4
    if total_endpoints <= 0:
        return 0.0
    return benchmark_errors / total_endpoints


def assert_build_meta_healthy(
    *,
    benchmark_errors: int,
    model_count: int,
    max_error_ratio: float = MAX_BENCHMARK_ERROR_RATIO,
) -> None:
    ratio = benchmark_error_ratio(benchmark_errors, model_count)
    if ratio > max_error_ratio:
        raise BenchmarkHealthError(
            f"Benchmark fetch unhealthy: {benchmark_errors} errors for "
            f"{model_count} models ({ratio:.1%} error rate, "
            f"threshold {max_error_ratio:.0%})"
        )
