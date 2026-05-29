from datetime import UTC, datetime, timedelta

from modelwatch.price_events import (
    DROP_LOOKBACK_HOURS,
    events_in_last_hours,
    load_price_events,
    records_from_events,
)
from modelwatch.schemas import PriceEventRecord


def _event(
    *,
    detected_at: datetime,
    model_id: str = "acme/model",
) -> PriceEventRecord:
    return PriceEventRecord(
        detected_at=detected_at,
        model_id=model_id,
        field="prompt",
        old_per_million_usd="3.000000",
        new_per_million_usd="2.000000",
        pct_drop=0.333333,
        saved_per_million_usd="1.000000",
    )


def test_events_in_last_hours_includes_recent_only() -> None:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    events = [
        _event(detected_at=now - timedelta(hours=1)),
        _event(detected_at=now - timedelta(hours=25)),
        _event(detected_at=now - timedelta(hours=23)),
    ]

    filtered = events_in_last_hours(events, DROP_LOOKBACK_HOURS, now=now)

    assert len(filtered) == 2


def test_records_from_events_maps_detected_at() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    event = _event(detected_at=at)

    records = records_from_events([event])

    assert len(records) == 1
    assert records[0].detected_at == at
    assert records[0].model_id == "acme/model"


def test_load_price_events_reads_jsonl(tmp_path: object) -> None:
    from pathlib import Path

    path = Path(str(tmp_path)) / "events.jsonl"
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    event = _event(detected_at=at)
    path.write_text(event.model_dump_json() + "\n", encoding="utf-8")

    loaded = load_price_events(path)

    assert len(loaded) == 1
    assert loaded[0].model_id == "acme/model"
