def is_latest_alias_model_id(model_id: str) -> bool:
    return model_id.startswith("~") or model_id.endswith("-latest")
