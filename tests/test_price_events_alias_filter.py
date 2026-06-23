from datetime import UTC, datetime, timedelta

import pytest

from modelwatch.price_events import (
    DROP_LOOKBACK_HOURS,
    drops_in_last_hours,
)
from modelwatch.schemas import PriceEventRecord


def _event(
    *,
    detected_at: datetime,
    model_id: str,
) -> PriceEventRecord:
    return PriceEventRecord(
        detected_at=detected_at,
        model_id=model_id,
        field="input_cache_read",
        old_per_million_usd="0.270414",
        new_per_million_usd="0.144000",
        pct_drop=0.46748278500382556,
        saved_per_million_usd="0.126414",
    )


def test_drops_in_last_hours_excludes_latest_alias_models() -> None:
    now = datetime(2026, 6, 23, 21, 0, tzinfo=UTC)
    at = now - timedelta(hours=1)
    events = [
        _event(detected_at=at, model_id="~moonshotai/kimi-latest"),
        _event(detected_at=at, model_id="moonshotai/kimi-k2.6"),
    ]

    drops = drops_in_last_hours(events, DROP_LOOKBACK_HOURS, now=now)

    assert len(drops) == 1
    assert drops[0].model_id == "moonshotai/kimi-k2.6"
