export interface ChartDomain {
  min: number;
  max: number;
}

export interface TimeDomain {
  start: number;
  end: number;
}

export interface ChartGap {
  /** Index of the last recorded point before the gap. */
  startIndex: number;
  /** Index of the first recorded point after the gap. */
  endIndex: number;
  startAt: number;
  endAt: number;
  durationMs: number;
}

export interface TimeTick {
  time: number;
  x: number;
}

export interface HistoryWindow<T> {
  points: T[];
  /** Requested window start (ms epoch) when a bounded range is selected. */
  windowStart: number | null;
  windowEnd: number | null;
  /** True when a point recorded before the window start is kept to anchor the line. */
  carryIn: boolean;
}

export const HOUR_MS = 3_600_000;
export const DAY_MS = 86_400_000;
/** History appends a heartbeat point every 24h, so a longer gap means builds were missed. */
export const HEARTBEAT_MS = 24 * HOUR_MS;
export const DEFAULT_GAP_MS = HEARTBEAT_MS * 1.5;

export function computeChartDomain(values: number[]): ChartDomain {
  if (values.length === 0) {
    return { min: 0, max: 1 };
  }
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  if (rawMin === rawMax) {
    const pad = rawMin === 0 ? 1 : rawMin * 0.1;
    return { min: Math.max(0, rawMin - pad), max: rawMax + pad };
  }
  return { min: rawMin * 0.95, max: rawMax * 1.05 };
}

export function yAxisTickValues(
  min: number,
  max: number,
  count = 5,
): number[] {
  const range = max - min || 1;
  return Array.from(
    { length: count },
    (_, index) => max - (range * index) / (count - 1),
  );
}

export function formatChartAxisUsd(value: number): string {
  if (value === 0) {
    return "$0";
  }
  if (value < 0.01) {
    return `$${value.toFixed(4)}`;
  }
  if (value < 1) {
    return `$${value.toFixed(3)}`;
  }
  return `$${value.toFixed(2)}`;
}

export function computeTimeDomain(times: number[]): TimeDomain {
  if (times.length === 0) {
    return { start: 0, end: 1 };
  }
  const start = Math.min(...times);
  const end = Math.max(...times);
  return start === end ? { start, end: start + 1 } : { start, end };
}

/**
 * Axis domain for a chart: the requested window when one is selected (clamped to
 * the recorded data), otherwise the full extent of the points.
 */
export function resolveTimeDomain(
  times: number[],
  windowStart: number | null = null,
  windowEnd: number | null = null,
): TimeDomain {
  const base = computeTimeDomain(times);
  if (windowStart === null) {
    return base;
  }
  const start = Math.max(windowStart, base.start);
  const end = windowEnd ?? base.end;
  return start >= end ? base : { start, end };
}

export function timeToX(
  time: number,
  domain: TimeDomain,
  width: number,
): number {
  const span = domain.end - domain.start || 1;
  return ((time - domain.start) / span) * width;
}

export function xToTime(
  x: number,
  domain: TimeDomain,
  width: number,
): number {
  if (width <= 0) {
    return domain.start;
  }
  const span = domain.end - domain.start || 1;
  return domain.start + (x / width) * span;
}

export function timeAxisTicks(
  domain: TimeDomain,
  width: number,
  count = 5,
): TimeTick[] {
  if (count <= 1) {
    return [{ time: domain.start, x: timeToX(domain.start, domain, width) }];
  }
  return Array.from({ length: count }, (_, index) => {
    const time =
      domain.start + ((domain.end - domain.start) * index) / (count - 1);
    return { time, x: timeToX(time, domain, width) };
  });
}

/**
 * Gaps are consecutive recorded points spaced further apart than the heartbeat
 * cadence, i.e. builds that never ran. `times` must be ascending.
 */
export function detectHistoryGaps(
  times: number[],
  minGapMs = DEFAULT_GAP_MS,
): ChartGap[] {
  const gaps: ChartGap[] = [];
  for (let index = 1; index < times.length; index += 1) {
    const durationMs = times[index] - times[index - 1];
    if (durationMs > minGapMs) {
      gaps.push({
        startIndex: index - 1,
        endIndex: index,
        startAt: times[index - 1],
        endAt: times[index],
        durationMs,
      });
    }
  }
  return gaps;
}

export function gapContainingTime(
  gaps: ChartGap[],
  time: number,
): ChartGap | null {
  return (
    gaps.find((gap) => time > gap.startAt && time < gap.endAt) ?? null
  );
}

export function nearestPointIndexByTime(time: number, times: number[]): number {
  if (times.length === 0) {
    return 0;
  }
  let low = 0;
  let high = times.length - 1;
  while (low < high) {
    const mid = (low + high) >> 1;
    if (times[mid] < time) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  const after = low;
  const before = Math.max(0, low - 1);
  return Math.abs(times[before] - time) <= Math.abs(times[after] - time)
    ? before
    : after;
}

export function formatGapDuration(durationMs: number): string {
  if (durationMs < HOUR_MS) {
    return `${Math.max(1, Math.round(durationMs / 60_000))}m`;
  }
  if (durationMs < 2 * DAY_MS) {
    return `${Math.round(durationMs / HOUR_MS)}h`;
  }
  return `${Math.max(1, Math.floor(durationMs / DAY_MS))}d`;
}

export function totalGapDuration(gaps: ChartGap[]): number {
  return gaps.reduce((sum, gap) => sum + gap.durationMs, 0);
}

/**
 * Restrict history to a trailing window. The point preceding the window start is
 * kept so the line is anchored where it enters the window; `spanMs === null`
 * keeps everything.
 */
export function windowHistoryPoints<T extends { at: Date }>(
  points: T[],
  spanMs: number | null,
): HistoryWindow<T> {
  if (spanMs === null || points.length === 0) {
    return { points, windowStart: null, windowEnd: null, carryIn: false };
  }
  const times = points.map((point) => point.at.getTime());
  const windowEnd = times[times.length - 1];
  const windowStart = windowEnd - spanMs;
  let firstInWindow = times.findIndex((time) => time >= windowStart);
  if (firstInWindow === -1) {
    firstInWindow = points.length - 1;
  }
  const carryIn = firstInWindow > 0;
  return {
    points: points.slice(carryIn ? firstInWindow - 1 : firstInWindow),
    windowStart,
    windowEnd,
    carryIn,
  };
}

export function valueToY(
  value: number,
  min: number,
  max: number,
  height: number,
): number {
  const range = max - min || 1;
  return height - ((value - min) / range) * height;
}
