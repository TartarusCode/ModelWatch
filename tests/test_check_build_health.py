import json
from pathlib import Path

import pytest

from modelwatch.check_build_health import check_build_meta_file


def test_assert_build_meta_from_file_passes(tmp_path: Path) -> None:
    meta_path = tmp_path / "meta.json"
    meta_path.write_text(
        json.dumps({"benchmark_errors": 5, "model_count": 100}),
        encoding="utf-8",
    )
    check_build_meta_file(meta_path)


def test_assert_build_meta_from_file_fails(tmp_path: Path) -> None:
    meta_path = tmp_path / "meta.json"
    meta_path.write_text(
        json.dumps({"benchmark_errors": 676, "model_count": 338}),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc_info:
        check_build_meta_file(meta_path)
    assert exc_info.value.code == 1
