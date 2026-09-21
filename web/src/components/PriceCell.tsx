import {
  formatPerMillion,
  formatScheduleRange,
  parseTokenPrice,
} from "../lib/pricing";
import type { PricingSchedule } from "../types";

interface PriceCellProps {
  perToken: string;
  field?: string;
  schedule?: PricingSchedule | null;
  /** Tooltip text: the schedule's windows in the viewer's local time. */
  scheduleNote?: string | null;
}

export function PriceCell({
  perToken,
  field,
  schedule = null,
  scheduleNote = null,
}: PriceCellProps) {
  const range = field ? formatScheduleRange(schedule, field) : null;
  if (range && field) {
    const tierCount = schedule?.rates?.[field]?.length ?? 2;
    return (
      <span
        className="price-cell price-cell--scheduled"
        title={scheduleNote ?? undefined}
      >
        {range}
        <span className="tier-chip">{tierCount} tiers</span>
      </span>
    );
  }

  const parsed = parseTokenPrice(perToken);
  const className =
    parsed.kind === "free"
      ? "price-cell price-cell--free"
      : parsed.kind === "variable"
        ? "price-cell price-cell--varies"
        : "price-cell";
  return (
    <span className={className}>{formatPerMillion(perToken, field)}</span>
  );
}
