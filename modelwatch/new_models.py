from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from modelwatch.schemas import (
    ModelSnapshot,
    NewModelEventRecord,
    NewModelRecord,
    PreviousSnapshot,
)

NEW_MODEL_LOOKBACK_HOURS = 24


@dataclass(frozen=True)
class NewModelAddition:
    model_id: str
    name: str
    canonical_slug: str
    created: int


def detect_new_models(
    current: list[ModelSnapshot],
    *,
    previous: PreviousSnapshot | None,
) -> list[NewModelAddition]:
    if previous is None:
        return []
    previous_ids = set(previous.models.keys())
    additions = [
        NewModelAddition(
            model_id=model.id,
            name=model.name,
            canonical_slug=model.canonical_slug,
            created=model.created,
        )
        for model in current
        if model.id not in previous_ids
    ]
    return sorted(additions, key=lambda item: item.model_id)


def load_new_model_events(path: Path) -> list[NewModelEventRecord]:
    if not path.exists():
        return []
    events: list[NewModelEventRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(NewModelEventRecord.model_validate_json(line))
    return events


def events_in_last_hours(
    events: list[NewModelEventRecord],
    hours: int,
    *,
    now: datetime,
) -> list[NewModelEventRecord]:
    cutoff = now - timedelta(hours=hours)
    return [event for event in events if event.detected_at >= cutoff]


def records_from_events(events: list[NewModelEventRecord]) -> list[NewModelRecord]:
    return [
        NewModelRecord(
            detected_at=event.detected_at,
            model_id=event.model_id,
            name=event.name,
            canonical_slug=event.canonical_slug,
            created=event.created,
        )
        for event in events
    ]


def models_in_last_hours(
    events: list[NewModelEventRecord],
    hours: int,
    *,
    now: datetime,
) -> list[NewModelRecord]:
    recent = events_in_last_hours(events, hours, now=now)
    sorted_events = sorted(recent, key=lambda event: event.detected_at, reverse=True)
    return records_from_events(sorted_events)
