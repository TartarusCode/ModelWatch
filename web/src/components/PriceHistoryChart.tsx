import type { ChartPoint } from "../lib/priceHistory";

interface PriceHistoryChartProps {
  points: ChartPoint[];
}

interface SeriesLine {
  key: "prompt" | "completion";
  label: string;
  color: string;
}

function buildSeries(points: ChartPoint[]): SeriesLine[] {
  const hasPrompt = points.some((p) => p.prompt !== null);
  const hasCompletion = points.some((p) => p.completion !== null);
  const series: SeriesLine[] = [];
  if (hasPrompt) {
    series.push({ key: "prompt", label: "Prompt", color: "#a78bfa" });
  }
  if (hasCompletion) {
    series.push({ key: "completion", label: "Completion", color: "#4ade80" });
  }
  return series;
}

function linePath(
  points: ChartPoint[],
  key: "prompt" | "completion",
  width: number,
  height: number,
  min: number,
  max: number,
): string {
  const range = max - min || 1;
  const step = points.length > 1 ? width / (points.length - 1) : 0;
  const segments: string[] = [];
  let started = false;
  points.forEach((point, index) => {
    const value = point[key];
    if (value === null) {
      started = false;
      return;
    }
    const x = index * step;
    const y = height - ((value - min) / range) * height;
    segments.push(`${started ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`);
    started = true;
  });
  return segments.join(" ");
}

function allNumericValues(points: ChartPoint[]): number[] {
  return points.flatMap((p) =>
    [p.prompt, p.completion].filter((v): v is number => v !== null),
  );
}

export function PriceHistoryChart({ points }: PriceHistoryChartProps) {
  const series = buildSeries(points);
  if (series.length === 0) {
    return (
      <p className="muted" style={{ marginBottom: "1rem" }}>
        No numeric pricing history (variable or free pricing only).
      </p>
    );
  }

  const allValues = allNumericValues(points);
  const min = Math.min(...allValues) * 0.95;
  const max = Math.max(...allValues) * 1.05;
  const width = 640;
  const height = 160;

  const firstAt = points[0]?.at;
  const lastAt = points[points.length - 1]?.at;

  return (
    <div className="price-chart">
      <div className="price-chart__legend">
        {series.map((s) => (
          <span key={s.key} className="price-chart__legend-item">
            <span
              className="price-chart__swatch"
              style={{ backgroundColor: s.color }}
            />
            {s.label}
          </span>
        ))}
      </div>
      <svg
        className="price-chart__svg"
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label="Price history chart"
      >
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const y = height * frac;
          return (
            <line
              key={frac}
              x1={0}
              y1={y}
              x2={width}
              y2={y}
              className="price-chart__grid"
            />
          );
        })}
        {series.map((s) => (
          <path
            key={s.key}
            d={linePath(points, s.key, width, height, min, max)}
            fill="none"
            stroke={s.color}
            strokeWidth={2}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
      <div className="price-chart__axis">
        <span>
          {firstAt?.toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          })}
        </span>
        <span className="tabular-nums muted">
          ${min.toFixed(2)} – ${max.toFixed(2)} /M
        </span>
        <span>
          {lastAt?.toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          })}
        </span>
      </div>
    </div>
  );
}
