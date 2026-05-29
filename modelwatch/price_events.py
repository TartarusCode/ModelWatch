from datetime import UTC, datetime, timedelta
from pathlib import Path

from modelwatch.schemas import PriceDropRecord, PriceEventRecord

DROP_LOOKBACK_HOURS = 24


def load_price_events(path: Path) -> list[PriceEventRecord]:
    if not path.exists():
        return []
    events: list[PriceEventRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(PriceEventRecord.model_validate_json(line))
    return events


def events_in_last_hours(
    events: list[PriceEventRecord],
    hours: int,
    *,
    now: datetime,
) -> list[PriceEventRecord]:
    cutoff = now - timedelta(hours=hours)
    return [event for event in events if event.detected_at >= cutoff]


def records_from_events(events: list[PriceEventRecord]) -> list[PriceDropRecord]:
    return [
        PriceDropRecord(
            detected_at=event.detected_at,
            model_id=event.model_id,
            field=event.field,
            old_per_million_usd=event.old_per_million_usd,
            new_per_million_usd=event.new_per_million_usd,
            pct_drop=event.pct_drop,
            saved_per_million_usd=event.saved_per_million_usd,
        )
        for event in events
    ]


def drops_in_last_hours(
    events: list[PriceEventRecord],
    hours: int,
    *,
    now: datetime,
) -> list[PriceDropRecord]:
    recent = events_in_last_hours(events, hours, now=now)
    sorted_events = sorted(recent, key=lambda event: event.detected_at, reverse=True)
    return records_from_events(sorted_events)
