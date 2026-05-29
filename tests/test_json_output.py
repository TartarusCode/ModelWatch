import json

from pydantic import BaseModel, ConfigDict

from modelwatch.json_output import dump_model, dump_model_line, dumps_json


def test_dumps_json_sorts_top_level_keys() -> None:
    left = {"z": 1, "a": 2}
    right = {"a": 2, "z": 1}
    assert dumps_json(left) == dumps_json(right)


def test_dumps_json_sorts_nested_keys() -> None:
    left = {"outer": {"z": 1, "a": 2}}
    right = {"outer": {"a": 2, "z": 1}}
    assert dumps_json(left) == dumps_json(right)


class SampleModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    zebra: str
    alpha: int


def test_dump_model_uses_sorted_keys() -> None:
    model = SampleModel(zebra="z", alpha=1)
    payload = json.loads(dump_model(model))
    assert list(payload.keys()) == ["alpha", "zebra"]


def test_dump_model_line_is_compact_sorted() -> None:
    model = SampleModel(zebra="z", alpha=1)
    assert dump_model_line(model) == '{"alpha":1,"zebra":"z"}'
