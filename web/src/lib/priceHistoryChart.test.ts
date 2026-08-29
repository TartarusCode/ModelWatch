import { describe, expect, it } from "vitest";
import {
  computeChartDomain,
  formatChartAxisUsd,
  nearestPointIndex,
  pointX,
  valueToY,
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

describe("nearestPointIndex", () => {
  it("snaps to the closest point", () => {
    expect(nearestPointIndex(0, 100, 3)).toBe(0);
    expect(nearestPointIndex(49, 100, 3)).toBe(1);
    expect(nearestPointIndex(100, 100, 3)).toBe(2);
  });
});

describe("pointX", () => {
  it("maps index to plot coordinates", () => {
    expect(pointX(0, 100, 3)).toBe(0);
    expect(pointX(2, 100, 3)).toBe(100);
  });
});

describe("valueToY", () => {
  it("maps values into svg coordinates", () => {
    expect(valueToY(0, 0, 10, 100)).toBe(100);
    expect(valueToY(10, 0, 10, 100)).toBe(0);
    expect(valueToY(5, 0, 10, 100)).toBe(50);
  });
});
