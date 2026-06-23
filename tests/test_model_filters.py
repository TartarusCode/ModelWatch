import pytest

from modelwatch.model_filters import is_latest_alias_model_id


@pytest.mark.parametrize(
    "model_id",
    [
        "~anthropic/claude-sonnet-latest",
        "~moonshotai/kimi-latest",
        "openai/gpt-chat-latest",
    ],
)
def test_latest_alias_model_ids_are_filtered(model_id: str) -> None:
    assert is_latest_alias_model_id(model_id) is True


@pytest.mark.parametrize(
    "model_id",
    [
        "anthropic/claude-4.6-sonnet-20260217",
        "moonshotai/kimi-k2.7-code",
        "openai/gpt-4o",
        "google/gemini-2.5-flash-lite",
    ],
)
def test_versioned_model_ids_are_kept(model_id: str) -> None:
    assert is_latest_alias_model_id(model_id) is False
