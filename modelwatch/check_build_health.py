import json
import sys
from pathlib import Path

from modelwatch.benchmark_health import BenchmarkHealthError, assert_build_meta_healthy

META_PATH = (
    Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "meta.json"
)


def check_build_meta_file(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    benchmark_errors = int(payload["benchmark_errors"])
    model_count = int(payload["model_count"])
    try:
        assert_build_meta_healthy(
            benchmark_errors=benchmark_errors,
            model_count=model_count,
        )
    except BenchmarkHealthError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


def main() -> None:
    check_build_meta_file(META_PATH)


if __name__ == "__main__":
    main()
