from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from modelwatch.price_drop_state import FieldDropState, PriceDropStateStore
from modelwatch.price_events import (
    DROP_LOOKBACK_HOURS,
    build_price_drops_output,
    episodes_for_display,
    recovered_in_last_hours,
)
from modelwatch.schemas import PriceDropRecord


def _episode(
    *,
    detected_at: datetime,
    model_id: str = "acme/model",
    field: str = "prompt",
    status: Literal["active", "recovered"] = "active",
    new_per_million_usd: str = "0.800000",
    recovered_at: datetime | None = None,
) -> PriceDropRecord:
    return PriceDropRecord(
        detected_at=detected_at,
        model_id=model_id,
        field=field,
        episode_start_per_million_usd="1.000000",
        old_per_million_usd="1.000000",
        new_per_million_usd=new_per_million_usd,
        pct_drop=0.2,
        saved_per_million_usd="0.200000",
        status=status,
        recovered_at=recovered_at,
        recovered_per_million_usd="0.950000" if recovered_at else None,
    )


def test_build_price_drops_output_uses_state_for_active() -> None:
    now = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    stale_episode = PriceDropRecord(
        detected_at=now - timedelta(hours=1),
        model_id="acme/model",
        field="prompt",
        episode_start_per_million_usd="1.000000",
        old_per_million_usd="1.000000",
        new_per_million_usd="0.800000",
        pct_drop=0.2,
        saved_per_million_usd="0.200000",
        status="active",
    )
    store = PriceDropStateStore(
        generated_at=now,
        models={
            "acme/model": {
                "prompt": FieldDropState.idle(Decimal("0.950000")),
            },
        },
        episodes=[stale_episode],
    )

    active, recovered, display = build_price_drops_output(
        store,
        now=now,
        window_hours=DROP_LOOKBACK_HOURS,
    )

    assert active == []
    assert len(display) == 1


def test_recovered_in_last_hours_filters_by_recovery_time() -> None:
    now = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    episodes = [
        _episode(
            detected_at=now - timedelta(days=2),
            status="recovered",
            recovered_at=now - timedelta(hours=2),
        ),
        _episode(
            detected_at=now - timedelta(days=3),
            status="recovered",
            recovered_at=now - timedelta(days=2),
        ),
    ]
    recovered = recovered_in_last_hours(
        episodes,
        DROP_LOOKBACK_HOURS,
        now=now,
    )
    assert len(recovered) == 1


def test_episodes_for_display_excludes_latest_aliases() -> None:
    episodes = [
        _episode(detected_at=datetime(2026, 7, 7, 12, 0, tzinfo=UTC)),
        _episode(
            detected_at=datetime(2026, 7, 7, 12, 0, tzinfo=UTC),
            model_id="openai/gpt-4o-latest",
        ),
    ]
    assert len(episodes_for_display(episodes)) == 1
