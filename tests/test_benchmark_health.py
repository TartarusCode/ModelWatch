from modelwatch.benchmark_health import (
    BenchmarkHealthError,
    ProbeResult,
    assert_build_meta_healthy,
    benchmark_error_ratio,
    endpoint_is_healthy,
    probes_indicate_broken_endpoints,
)


def test_endpoint_is_healthy_on_200_with_data_key() -> None:
    assert endpoint_is_healthy(200, {"data": []}) is True
    assert endpoint_is_healthy(200, {"data": {"records": []}}) is True


def test_endpoint_is_unhealthy_on_non_200() -> None:
    assert endpoint_is_healthy(404, {"data": []}) is False
    assert endpoint_is_healthy(500, {"error": "fail"}) is False


def test_endpoint_is_unhealthy_when_data_key_missing() -> None:
    assert endpoint_is_healthy(200, {"error": "fail"}) is False


def test_probes_indicate_broken_when_all_fail() -> None:
    results = [
        ProbeResult(endpoint="design", slug="a/b", status_code=404, ok=False),
        ProbeResult(endpoint="aa", slug="a/b", status_code=404, ok=False),
    ]
    assert probes_indicate_broken_endpoints(results) is True


def test_probes_ok_when_at_least_one_succeeds() -> None:
    results = [
        ProbeResult(endpoint="design", slug="a/b", status_code=404, ok=False),
        ProbeResult(endpoint="aa", slug="a/b", status_code=200, ok=True),
    ]
    assert probes_indicate_broken_endpoints(results) is False


def test_benchmark_error_ratio() -> None:
    assert benchmark_error_ratio(676, 338) == 1.0
    assert benchmark_error_ratio(0, 338) == 0.0
    assert benchmark_error_ratio(100, 338) == 100 / 676


def test_assert_build_meta_healthy_passes_below_threshold() -> None:
    assert_build_meta_healthy(benchmark_errors=10, model_count=338)


def test_assert_build_meta_healthy_fails_above_threshold() -> None:
    try:
        assert_build_meta_healthy(benchmark_errors=676, model_count=338)
    except BenchmarkHealthError as exc:
        assert "676" in str(exc)
        assert "338" in str(exc)
    else:
        raise AssertionError("expected BenchmarkHealthError")
