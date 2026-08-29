export interface ChartDomain {
  min: number;
  max: number;
}

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

export function nearestPointIndex(
  relativeX: number,
  plotWidth: number,
  pointCount: number,
): number {
  if (pointCount <= 0) {
    return 0;
  }
  if (pointCount === 1) {
    return 0;
  }
  const step = plotWidth / (pointCount - 1);
  const index = Math.round(relativeX / step);
  return Math.max(0, Math.min(pointCount - 1, index));
}

export function pointX(
  index: number,
  plotWidth: number,
  pointCount: number,
): number {
  if (pointCount <= 1) {
    return plotWidth / 2;
  }
  return (index / (pointCount - 1)) * plotWidth;
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
