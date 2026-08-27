from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from modelwatch.price_change_state import FieldChangeState, PriceChangeStateStore
from modelwatch.price_changes import (
    CHANGE_LOOKBACK_HOURS,
    build_price_changes_output,
    episodes_for_display,
    recovered_changes_in_last_hours,
    settled_changes_in_last_hours,
)
from modelwatch.schemas import PriceChangeRecord


def _episode(
    *,
    detected_at: datetime,
    model_id: str = "acme/model",
    field: str = "prompt",
    direction: Literal["cut", "hike"] = "cut",
    status: Literal["active", "recovered", "settled"] = "active",
    new_per_million_usd: str = "0.800000",
    recovered_at: datetime | None = None,
    settled_at: datetime | None = None,
) -> PriceChangeRecord:
    if direction == "cut":
        pct_change = -0.2
        delta = "-0.200000"
        start = "1.000000"
    else:
        pct_change = 0.2
        delta = "0.200000"
        start = "1.000000"
        new_per_million_usd = (
            "1.200000" if new_per_million_usd == "0.800000" else new_per_million_usd
        )
    return PriceChangeRecord(
        detected_at=detected_at,
        model_id=model_id,
        field=field,
        direction=direction,
        episode_start_per_million_usd=start,
        old_per_million_usd=start,
        new_per_million_usd=new_per_million_usd,
        pct_change=pct_change,
        delta_per_million_usd=delta,
        status=status,
        recovered_at=recovered_at,
        recovered_per_million_usd="0.950000" if recovered_at else None,
        settled_at=settled_at,
        settled_per_million_usd=new_per_million_usd if settled_at else None,
    )


def test_build_price_changes_output_uses_state_for_active() -> None:
    now = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    stale_episode = PriceChangeRecord(
        detected_at=now - timedelta(hours=1),
        model_id="acme/model",
        field="prompt",
        direction="cut",
        episode_start_per_million_usd="1.000000",
        old_per_million_usd="1.000000",
        new_per_million_usd="0.800000",
        pct_change=-0.2,
        delta_per_million_usd="-0.200000",
        status="active",
    )
    store = PriceChangeStateStore(
        generated_at=now,
        models={
            "acme/model": {
                "prompt": FieldChangeState.idle(Decimal("0.950000")),
            },
        },
        episodes=[stale_episode],
    )

    active, recovered, settled, display = build_price_changes_output(
        store,
        now=now,
        window_hours=CHANGE_LOOKBACK_HOURS,
    )

    assert active == []
    assert recovered == []
    assert settled == []
    assert len(display) == 1


def test_build_price_changes_output_includes_recent_settled() -> None:
    now = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    store = PriceChangeStateStore(
        generated_at=now,
        models={},
        episodes=[
            _episode(
                detected_at=now - timedelta(days=8),
                status="settled",
                settled_at=now - timedelta(hours=2),
            ),
            _episode(
                detected_at=now - timedelta(days=10),
                status="settled",
                settled_at=now - timedelta(days=2),
                field="completion",
            ),
        ],
    )

    _, _, settled, _ = build_price_changes_output(
        store,
        now=now,
        window_hours=CHANGE_LOOKBACK_HOURS,
    )

    assert len(settled) == 1
    assert settled[0].field == "prompt"


def test_recovered_changes_in_last_hours_filters_by_recovery_time() -> None:
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
    recovered = recovered_changes_in_last_hours(
        episodes,
        CHANGE_LOOKBACK_HOURS,
        now=now,
    )
    assert len(recovered) == 1


def test_settled_changes_in_last_hours_filters_by_settle_time() -> None:
    now = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    episodes = [
        _episode(
            detected_at=now - timedelta(days=8),
            status="settled",
            settled_at=now - timedelta(hours=1),
        ),
        _episode(
            detected_at=now - timedelta(days=9),
            status="settled",
            settled_at=now - timedelta(days=2),
            field="completion",
        ),
    ]
    settled = settled_changes_in_last_hours(episodes, CHANGE_LOOKBACK_HOURS, now=now)
    assert len(settled) == 1


def test_episodes_for_display_excludes_latest_aliases() -> None:
    episodes = [
        _episode(detected_at=datetime(2026, 7, 7, 12, 0, tzinfo=UTC)),
        _episode(
            detected_at=datetime(2026, 7, 7, 12, 0, tzinfo=UTC),
            model_id="openai/gpt-4o-latest",
        ),
    ]
    assert len(episodes_for_display(episodes)) == 1
