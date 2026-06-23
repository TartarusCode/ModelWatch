from datetime import UTC, datetime, timedelta

from modelwatch.price_events import (
    DROP_LOOKBACK_HOURS,
    dedupe_drop_events_for_display,
    dedupe_settled_price_re_alerts,
    drops_in_last_hours,
    filter_redundant_drop_events,
)
from modelwatch.schemas import PriceEventRecord


def _event(
    *,
    detected_at: datetime,
    model_id: str,
    field: str = "prompt",
    new_per_million_usd: str = "0.250000",
    old_per_million_usd: str = "0.500000",
) -> PriceEventRecord:
    return PriceEventRecord(
        detected_at=detected_at,
        model_id=model_id,
        field=field,
        old_per_million_usd=old_per_million_usd,
        new_per_million_usd=new_per_million_usd,
        pct_drop=0.5,
        saved_per_million_usd="0.250000",
    )


def test_drops_in_last_hours_keeps_latest_event_per_model_field() -> None:
    now = datetime(2026, 6, 23, 21, 0, tzinfo=UTC)
    events = [
        _event(
            detected_at=now - timedelta(hours=10),
            model_id="nex-agi/nex-n2-pro",
            old_per_million_usd="0.500000",
        ),
        _event(
            detected_at=now - timedelta(hours=1),
            model_id="nex-agi/nex-n2-pro",
            old_per_million_usd="0.416667",
        ),
    ]

    drops = drops_in_last_hours(events, DROP_LOOKBACK_HOURS, now=now)

    assert len(drops) == 1
    assert drops[0].model_id == "nex-agi/nex-n2-pro"
    assert drops[0].old_per_million_usd == "0.416667"


def test_dedupe_settled_price_re_alerts_removes_same_price_followups() -> None:
    events = [
        _event(
            detected_at=datetime(2026, 6, 23, 10, 0, tzinfo=UTC),
            model_id="nex-agi/nex-n2-pro",
        ),
        _event(
            detected_at=datetime(2026, 6, 23, 20, 0, tzinfo=UTC),
            model_id="nex-agi/nex-n2-pro",
            old_per_million_usd="0.416667",
        ),
    ]

    deduped = dedupe_settled_price_re_alerts(events)

    assert len(deduped) == 1
    assert deduped[0].old_per_million_usd == "0.500000"


def test_filter_redundant_drop_events_blocks_repeat_at_same_settled_price() -> None:
    existing = [
        _event(
            detected_at=datetime(2026, 6, 23, 10, 0, tzinfo=UTC),
            model_id="nex-agi/nex-n2-pro",
        ),
    ]
    incoming = [
        _event(
            detected_at=datetime(2026, 6, 23, 20, 0, tzinfo=UTC),
            model_id="nex-agi/nex-n2-pro",
            old_per_million_usd="0.416667",
        ),
    ]

    kept = filter_redundant_drop_events(incoming, existing=existing)

    assert kept == []


def test_filter_redundant_drop_events_allows_new_lower_price() -> None:
    existing = [
        _event(
            detected_at=datetime(2026, 6, 23, 10, 0, tzinfo=UTC),
            model_id="nex-agi/nex-n2-pro",
            new_per_million_usd="0.250000",
        ),
    ]
    incoming = [
        _event(
            detected_at=datetime(2026, 6, 23, 20, 0, tzinfo=UTC),
            model_id="nex-agi/nex-n2-pro",
            new_per_million_usd="0.200000",
            old_per_million_usd="0.250000",
        ),
    ]

    kept = filter_redundant_drop_events(incoming, existing=existing)

    assert len(kept) == 1
    assert kept[0].new_per_million_usd == "0.200000"


def test_dedupe_drop_events_for_display_keeps_distinct_fields() -> None:
    now = datetime(2026, 6, 23, 20, 0, tzinfo=UTC)
    events = [
        _event(detected_at=now, model_id="nex-agi/nex-n2-pro", field="prompt"),
        _event(
            detected_at=now,
            model_id="nex-agi/nex-n2-pro",
            field="completion",
            new_per_million_usd="1.000000",
        ),
    ]

    deduped = dedupe_drop_events_for_display(events)

    assert len(deduped) == 2
