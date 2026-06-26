from datetime import datetime, timedelta
from pathlib import Path

from modelwatch.model_filters import is_latest_alias_model_id
from modelwatch.pricing_glitch import is_spurious_zero_drop_event
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


def dedupe_drop_events_for_display(
    events: list[PriceEventRecord],
) -> list[PriceEventRecord]:
    latest_by_key: dict[tuple[str, str], PriceEventRecord] = {}
    for event in events:
        key = (event.model_id, event.field)
        current = latest_by_key.get(key)
        if current is None or event.detected_at > current.detected_at:
            latest_by_key[key] = event
    return sorted(
        latest_by_key.values(),
        key=lambda event: event.detected_at,
        reverse=True,
    )


def dedupe_settled_price_re_alerts(
    events: list[PriceEventRecord],
) -> list[PriceEventRecord]:
    settled_by_key: dict[tuple[str, str], str] = {}
    kept: list[PriceEventRecord] = []
    for event in sorted(events, key=lambda item: item.detected_at):
        key = (event.model_id, event.field)
        if settled_by_key.get(key) == event.new_per_million_usd:
            continue
        settled_by_key[key] = event.new_per_million_usd
        kept.append(event)
    return kept


def filter_redundant_drop_events(
    incoming: list[PriceEventRecord],
    *,
    existing: list[PriceEventRecord],
) -> list[PriceEventRecord]:
    latest_by_key: dict[tuple[str, str], PriceEventRecord] = {}
    for event in existing:
        key = (event.model_id, event.field)
        current = latest_by_key.get(key)
        if current is None or event.detected_at > current.detected_at:
            latest_by_key[key] = event
    return [
        event
        for event in incoming
        if latest_by_key.get((event.model_id, event.field)) is None
        or latest_by_key[(event.model_id, event.field)].new_per_million_usd
        != event.new_per_million_usd
    ]


def filter_spurious_zero_drop_events(
    events: list[PriceEventRecord],
) -> list[PriceEventRecord]:
    return [
        event
        for event in events
        if not is_spurious_zero_drop_event(event.model_id, event.new_per_million_usd)
    ]


def drops_in_last_hours(
    events: list[PriceEventRecord],
    hours: int,
    *,
    now: datetime,
) -> list[PriceDropRecord]:
    recent = events_in_last_hours(events, hours, now=now)
    filtered = [
        event for event in recent if not is_latest_alias_model_id(event.model_id)
    ]
    filtered = filter_spurious_zero_drop_events(filtered)
    deduped = dedupe_drop_events_for_display(filtered)
    return records_from_events(deduped)
