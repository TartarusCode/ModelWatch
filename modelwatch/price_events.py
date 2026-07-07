from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from modelwatch.model_filters import is_latest_alias_model_id
from modelwatch.price_drop_state import is_episode_active
from modelwatch.pricing_glitch import is_spurious_zero_drop_event
from modelwatch.schemas import PriceDropRecord, PriceEventRecord

DROP_LOOKBACK_HOURS = 24


def _parse_price_event_line(line: str) -> PriceEventRecord:
    import json

    raw = json.loads(line)
    if raw.get("episode_start_per_million_usd") is None:
        raw["episode_start_per_million_usd"] = raw.get("old_per_million_usd")
    if raw.get("status") is None:
        raw["status"] = "active"
    return PriceEventRecord.model_validate(raw)


def load_price_events(path: Path) -> list[PriceEventRecord]:
    if not path.exists():
        return []
    events: list[PriceEventRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(_parse_price_event_line(line))
    return events


def events_in_last_hours(
    events: list[PriceEventRecord],
    hours: int,
    *,
    now: datetime,
) -> list[PriceEventRecord]:
    cutoff = now - timedelta(hours=hours)
    return [event for event in events if event.detected_at >= cutoff]


def episode_to_record(episode: PriceDropRecord) -> PriceDropRecord:
    return episode


def episodes_to_event_records(
    episodes: list[PriceDropRecord],
) -> list[PriceEventRecord]:
    return [
        PriceEventRecord.model_validate(episode.model_dump()) for episode in episodes
    ]


def filter_spurious_zero_drop_events(
    events: list[PriceEventRecord],
) -> list[PriceEventRecord]:
    return [
        event
        for event in events
        if not is_spurious_zero_drop_event(event.model_id, event.new_per_million_usd)
    ]


def active_drops(
    episodes: list[PriceDropRecord],
    *,
    current_per_million_by_model: dict[str, dict[str, Decimal]],
) -> list[PriceDropRecord]:
    active: list[PriceDropRecord] = []
    for episode in episodes:
        if is_latest_alias_model_id(episode.model_id):
            continue
        if is_spurious_zero_drop_event(episode.model_id, episode.new_per_million_usd):
            continue
        if episode.status != "active":
            continue
        model_prices = current_per_million_by_model.get(episode.model_id, {})
        current = model_prices.get(episode.field)
        if current is None:
            continue
        if is_episode_active(episode, current):
            active.append(episode)
    return active


def recovered_in_last_hours(
    episodes: list[PriceDropRecord],
    hours: int,
    *,
    now: datetime,
) -> list[PriceDropRecord]:
    cutoff = now - timedelta(hours=hours)
    return [
        episode
        for episode in episodes
        if episode.status == "recovered"
        and episode.recovered_at is not None
        and episode.recovered_at >= cutoff
        and not is_latest_alias_model_id(episode.model_id)
    ]


def episodes_for_display(
    episodes: list[PriceDropRecord],
) -> list[PriceDropRecord]:
    return [
        episode
        for episode in episodes
        if not is_latest_alias_model_id(episode.model_id)
        and not is_spurious_zero_drop_event(
            episode.model_id, episode.new_per_million_usd
        )
    ]


def build_price_drops_output(
    episodes: list[PriceDropRecord],
    *,
    current_per_million_by_model: dict[str, dict[str, Decimal]],
    now: datetime,
    window_hours: int,
    thresholds: object,
) -> tuple[list[PriceDropRecord], list[PriceDropRecord], list[PriceDropRecord]]:
    filtered = episodes_for_display(episodes)
    active = active_drops(
        filtered,
        current_per_million_by_model=current_per_million_by_model,
    )
    recovered = recovered_in_last_hours(filtered, window_hours, now=now)
    return active, recovered, filtered
