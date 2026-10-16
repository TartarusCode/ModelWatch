import { describe, expect, it } from "vitest";
import {
  DAY_MS,
  HOUR_MS,
  computeChartDomain,
  computeTimeDomain,
  detectHistoryGaps,
  formatChartAxisUsd,
  formatGapDuration,
  gapContainingTime,
  nearestPointIndexByTime,
  resolveTimeDomain,
  timeAxisTicks,
  timeToX,
  totalGapDuration,
  valueToY,
  windowHistoryPoints,
  xToTime,
  yAxisTickValues,
} from "./priceHistoryChart";

describe("computeChartDomain", () => {
  it("pads distinct values for headroom", () => {
    expect(computeChartDomain([10, 20])).toEqual({ min: 9.5, max: 21 });
  });

  it("expands flat values", () => {
    expect(computeChartDomain([5, 5]).min).toBeLessThan(5);
    expect(computeChartDomain([5, 5]).max).toBeGreaterThan(5);
  });
});

describe("yAxisTickValues", () => {
  it("returns top-to-bottom ticks", () => {
    expect(yAxisTickValues(0, 10, 3)).toEqual([10, 5, 0]);
  });
});

describe("formatChartAxisUsd", () => {
  it("formats small and large prices", () => {
    expect(formatChartAxisUsd(0)).toBe("$0");
    expect(formatChartAxisUsd(0.004)).toBe("$0.0040");
    expect(formatChartAxisUsd(0.5)).toBe("$0.500");
    expect(formatChartAxisUsd(12.3)).toBe("$12.30");
  });
});

describe("computeTimeDomain", () => {
  it("spans the first and last observation", () => {
    expect(computeTimeDomain([1000, 5000])).toEqual({ start: 1000, end: 5000 });
  });

  it("keeps a non-zero span for a single observation", () => {
    expect(computeTimeDomain([1000])).toEqual({ start: 1000, end: 1001 });
  });

  it("falls back to a unit span for no observations", () => {
    expect(computeTimeDomain([])).toEqual({ start: 0, end: 1 });
  });
});

describe("resolveTimeDomain", () => {
  const day = DAY_MS;

  it("uses the full extent when no window is selected", () => {
    expect(resolveTimeDomain([0, 3 * day])).toEqual({ start: 0, end: 3 * day });
  });

  it("honours the requested window even when a carry-in point predates it", () => {
    const times = [0, 5 * day, 6 * day];
    expect(resolveTimeDomain(times, 5 * day, 6 * day)).toEqual({
      start: 5 * day,
      end: 6 * day,
    });
  });

  it("clamps to the first reading when the window is wider than the history", () => {
    const times = [10 * day, 12 * day];
    expect(resolveTimeDomain(times, 0, 12 * day)).toEqual({
      start: 10 * day,
      end: 12 * day,
    });
  });

  it("falls back to the data extent for a degenerate window", () => {
    const times = [3 * day, 3 * day + HOUR_MS];
    expect(resolveTimeDomain(times, 5 * day, 5 * day)).toEqual({
      start: 3 * day,
      end: 3 * day + HOUR_MS,
    });
  });
});

describe("timeToX / xToTime", () => {
  const domain = { start: 1000, end: 5000 };

  it("maps time onto plot width", () => {
    expect(timeToX(1000, domain, 100)).toBe(0);
    expect(timeToX(3000, domain, 100)).toBe(50);
    expect(timeToX(5000, domain, 100)).toBe(100);
  });

  it("round-trips pixels back to time", () => {
    expect(xToTime(0, domain, 100)).toBe(1000);
    expect(xToTime(25, domain, 100)).toBe(2000);
    expect(xToTime(timeToX(4200, domain, 100), domain, 100)).toBeCloseTo(4200);
  });

  it("does not divide by a zero width", () => {
    expect(xToTime(10, domain, 0)).toBe(1000);
  });
});

describe("timeAxisTicks", () => {
  it("spaces ticks evenly in time across the plot", () => {
    const ticks = timeAxisTicks({ start: 0, end: 1000 }, 100, 3);
    expect(ticks).toEqual([
      { time: 0, x: 0 },
      { time: 500, x: 50 },
      { time: 1000, x: 100 },
    ]);
  });
});

describe("detectHistoryGaps", () => {
  const hour = HOUR_MS;

  it("ignores spacing within the heartbeat cadence", () => {
    const times = [0, hour, 25 * hour, 49 * hour];
    expect(detectHistoryGaps(times)).toEqual([]);
  });

  it("flags spacing beyond the heartbeat cadence", () => {
    const start = Date.UTC(2026, 9, 12, 3, 0);
    const end = Date.UTC(2026, 9, 16, 20, 52);
    const gaps = detectHistoryGaps([start - hour, start, end]);
    expect(gaps).toHaveLength(1);
    expect(gaps[0].startAt).toBe(start);
    expect(gaps[0].endAt).toBe(end);
    expect(gaps[0].startIndex).toBe(1);
    expect(gaps[0].endIndex).toBe(2);
    expect(gaps[0].durationMs).toBe(end - start);
  });

  it("accepts a custom threshold", () => {
    expect(detectHistoryGaps([0, 2 * hour], 12 * hour)).toHaveLength(0);
    expect(detectHistoryGaps([0, 2 * hour], 1 * hour)).toHaveLength(1);
  });
});

describe("gapContainingTime", () => {
  const gap = {
    startIndex: 0,
    endIndex: 1,
    startAt: 1000,
    endAt: 5000,
    durationMs: 4000,
  };

  it("finds the gap a hover lands inside", () => {
    expect(gapContainingTime([gap], 3000)).toBe(gap);
  });

  it("treats the recorded edges as data, not gap", () => {
    expect(gapContainingTime([gap], 1000)).toBeNull();
    expect(gapContainingTime([gap], 5000)).toBeNull();
    expect(gapContainingTime([gap], 500)).toBeNull();
  });
});

describe("nearestPointIndexByTime", () => {
  const times = [0, 1000, 5000];

  it("snaps to the closest observation in time", () => {
    expect(nearestPointIndexByTime(-100, times)).toBe(0);
    expect(nearestPointIndexByTime(400, times)).toBe(0);
    expect(nearestPointIndexByTime(600, times)).toBe(1);
    expect(nearestPointIndexByTime(4000, times)).toBe(2);
    expect(nearestPointIndexByTime(99999, times)).toBe(2);
  });

  it("handles an empty series", () => {
    expect(nearestPointIndexByTime(100, [])).toBe(0);
  });
});

describe("formatGapDuration", () => {
  it("uses minutes, hours then days", () => {
    expect(formatGapDuration(30 * 60_000)).toBe("30m");
    expect(formatGapDuration(4 * HOUR_MS)).toBe("4h");
    expect(formatGapDuration(26 * HOUR_MS)).toBe("26h");
    expect(formatGapDuration(4 * DAY_MS + 18 * HOUR_MS)).toBe("4d");
  });
});

describe("totalGapDuration", () => {
  it("sums gap lengths", () => {
    const gaps = detectHistoryGaps([0, 10 * DAY_MS, 20 * DAY_MS], DAY_MS);
    expect(totalGapDuration(gaps)).toBe(20 * DAY_MS);
    expect(totalGapDuration([])).toBe(0);
  });
});

describe("windowHistoryPoints", () => {
  const at = (day: number) => ({ at: new Date(Date.UTC(2026, 9, day)) });
  const points = [at(1), at(5), at(9), at(13), at(16)];

  it("keeps everything when no span is given", () => {
    const windowed = windowHistoryPoints(points, null);
    expect(windowed.points).toHaveLength(5);
    expect(windowed.windowStart).toBeNull();
    expect(windowed.carryIn).toBe(false);
  });

  it("keeps the reading before the window to anchor the line", () => {
    const windowed = windowHistoryPoints(points, 4 * DAY_MS);
    expect(windowed.points.map((p) => p.at.getUTCDate())).toEqual([9, 13, 16]);
    expect(windowed.carryIn).toBe(true);
    expect(windowed.windowEnd).toBe(points[4].at.getTime());
  });

  it("does not carry in when the first reading is already in the window", () => {
    const windowed = windowHistoryPoints(points, 30 * DAY_MS);
    expect(windowed.points).toHaveLength(5);
    expect(windowed.carryIn).toBe(false);
  });

  it("handles empty history", () => {
    expect(windowHistoryPoints([], 4 * DAY_MS).points).toEqual([]);
  });
});

describe("valueToY", () => {
  it("maps values into svg coordinates", () => {
    expect(valueToY(0, 0, 10, 100)).toBe(100);
    expect(valueToY(10, 0, 10, 100)).toBe(0);
    expect(valueToY(5, 0, 10, 100)).toBe(50);
  });
});
