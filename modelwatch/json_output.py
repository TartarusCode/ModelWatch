import json

from pydantic import BaseModel


def dumps_json(data: object, *, indent: int | None = 2) -> str:
    return json.dumps(
        data,
        indent=indent,
        sort_keys=True,
        ensure_ascii=False,
    )


def dump_model(model: BaseModel, *, indent: int | None = 2) -> str:
    return dumps_json(model.model_dump(mode="json"), indent=indent)


def dump_model_line(model: BaseModel) -> str:
    return json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def write_model_json(path: object, model: BaseModel) -> None:
    from pathlib import Path

    file_path = Path(str(path))
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(dump_model(model, indent=2), encoding="utf-8")
