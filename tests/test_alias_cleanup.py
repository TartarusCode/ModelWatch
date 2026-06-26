from datetime import UTC, datetime

from modelwatch.alias_cleanup import filter_new_model_events, filter_price_events
from modelwatch.schemas import NewModelEventRecord, PriceEventRecord


def _zero_price_event(model_id: str) -> PriceEventRecord:
    return PriceEventRecord(
        detected_at=datetime(2026, 6, 25, 13, 30, tzinfo=UTC),
        model_id=model_id,
        field="prompt",
        old_per_million_usd="1.000000",
        new_per_million_usd="0.000000",
        pct_drop=1.0,
        saved_per_million_usd="1.000000",
    )


def _price_event(model_id: str) -> PriceEventRecord:
    return PriceEventRecord(
        detected_at=datetime(2026, 6, 23, 20, 0, tzinfo=UTC),
        model_id=model_id,
        field="prompt",
        old_per_million_usd="1.000000",
        new_per_million_usd="0.500000",
        pct_drop=0.5,
        saved_per_million_usd="0.500000",
    )


def _new_model_event(model_id: str) -> NewModelEventRecord:
    return NewModelEventRecord(
        detected_at=datetime(2026, 6, 9, 19, 30, tzinfo=UTC),
        model_id=model_id,
        name="Test",
        canonical_slug=model_id,
        created=1,
    )


def test_filter_price_events_removes_latest_aliases() -> None:
    events = [
        _price_event("moonshotai/kimi-k2.6"),
        _price_event("~moonshotai/kimi-latest"),
    ]
    filtered = filter_price_events(events)
    assert [event.model_id for event in filtered] == ["moonshotai/kimi-k2.6"]


def test_filter_new_model_events_removes_latest_aliases() -> None:
    events = [
        _new_model_event("anthropic/claude-fable-5"),
        _new_model_event("~anthropic/claude-fable-latest"),
    ]
    filtered = filter_new_model_events(events)
    assert [event.model_id for event in filtered] == ["anthropic/claude-fable-5"]


def test_filter_price_events_removes_spurious_zero_drops() -> None:
    events = [
        _price_event("moonshotai/kimi-k2.6"),
        _zero_price_event("moonshotai/kimi-k2.6"),
        _zero_price_event("cohere/north-mini-code:free"),
    ]
    filtered = filter_price_events(events)
    assert [event.model_id for event in filtered] == [
        "moonshotai/kimi-k2.6",
        "cohere/north-mini-code:free",
    ]
