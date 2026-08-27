from datetime import datetime, timedelta
from pathlib import Path

from modelwatch.model_filters import is_latest_alias_model_id
from modelwatch.price_change_state import (
    PriceChangeStateStore,
    active_changes_from_state,
)
from modelwatch.pricing_glitch import is_spurious_zero_drop_event
from modelwatch.schemas import PriceChangeEventRecord, PriceChangeRecord

CHANGE_LOOKBACK_HOURS = 24


def _parse_price_change_event_line(line: str) -> PriceChangeEventRecord:
    import json

    raw = json.loads(line)
    raw = migrate_legacy_change_event_dict(raw)
    return PriceChangeEventRecord.model_validate(raw)


def migrate_legacy_change_event_dict(raw: dict[str, object]) -> dict[str, object]:
    migrated = dict(raw)
    if migrated.get("episode_start_per_million_usd") is None:
        migrated["episode_start_per_million_usd"] = migrated.get(
            "old_per_million_usd",
        )
    if migrated.get("status") is None:
        migrated["status"] = "active"
    if "pct_drop" in migrated and "pct_change" not in migrated:
        pct_drop = migrated.pop("pct_drop")
        if isinstance(pct_drop, (int, float, str)):
            migrated["pct_change"] = -float(pct_drop)
        else:
            migrated["pct_change"] = 0.0
        migrated["direction"] = "cut"
    if "saved_per_million_usd" in migrated and "delta_per_million_usd" not in migrated:
        saved = migrated.pop("saved_per_million_usd")
        if saved is None:
            migrated["delta_per_million_usd"] = "0.000000"
        else:
            saved_str = str(saved)
            if saved_str.startswith("-"):
                migrated["delta_per_million_usd"] = saved_str
            else:
                migrated["delta_per_million_usd"] = f"-{saved_str}"
        migrated.setdefault("direction", "cut")
    if "direction" not in migrated:
        pct = migrated.get("pct_change")
        if isinstance(pct, (int, float)) and pct > 0:
            migrated["direction"] = "hike"
        else:
            migrated["direction"] = "cut"
    return migrated


def load_price_change_events(path: Path) -> list[PriceChangeEventRecord]:
    if not path.exists():
        return []
    events: list[PriceChangeEventRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(_parse_price_change_event_line(line))
    return events


def events_in_last_hours(
    events: list[PriceChangeEventRecord],
    hours: int,
    *,
    now: datetime,
) -> list[PriceChangeEventRecord]:
    cutoff = now - timedelta(hours=hours)
    return [event for event in events if event.detected_at >= cutoff]


def episodes_to_event_records(
    episodes: list[PriceChangeRecord],
) -> list[PriceChangeEventRecord]:
    return [
        PriceChangeEventRecord.model_validate(episode.model_dump())
        for episode in episodes
    ]


def filter_spurious_zero_change_events(
    events: list[PriceChangeEventRecord],
) -> list[PriceChangeEventRecord]:
    return [
        event
        for event in events
        if not is_spurious_zero_drop_event(event.model_id, event.new_per_million_usd)
    ]


def recovered_changes_in_last_hours(
    episodes: list[PriceChangeRecord],
    hours: int,
    *,
    now: datetime,
) -> list[PriceChangeRecord]:
    cutoff = now - timedelta(hours=hours)
    return [
        episode
        for episode in episodes
        if episode.status == "recovered"
        and episode.recovered_at is not None
        and episode.recovered_at >= cutoff
        and not is_latest_alias_model_id(episode.model_id)
    ]


def settled_changes_in_last_hours(
    episodes: list[PriceChangeRecord],
    hours: int,
    *,
    now: datetime,
) -> list[PriceChangeRecord]:
    cutoff = now - timedelta(hours=hours)
    return [
        episode
        for episode in episodes
        if episode.status == "settled"
        and episode.settled_at is not None
        and episode.settled_at >= cutoff
        and not is_latest_alias_model_id(episode.model_id)
    ]


def episodes_for_display(
    episodes: list[PriceChangeRecord],
) -> list[PriceChangeRecord]:
    return [
        episode
        for episode in episodes
        if not is_latest_alias_model_id(episode.model_id)
        and not is_spurious_zero_drop_event(
            episode.model_id, episode.new_per_million_usd
        )
    ]


def build_price_changes_output(
    store: PriceChangeStateStore,
    *,
    now: datetime,
    window_hours: int,
) -> tuple[
    list[PriceChangeRecord],
    list[PriceChangeRecord],
    list[PriceChangeRecord],
    list[PriceChangeRecord],
]:
    filtered = episodes_for_display(store.episodes)
    active = active_changes_from_state(store)
    recovered = recovered_changes_in_last_hours(filtered, window_hours, now=now)
    settled = settled_changes_in_last_hours(filtered, window_hours, now=now)
    return active, recovered, settled, filtered
