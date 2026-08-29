import { useCallback, useRef, useState } from "react";
import {
  CHART_SERIES_COLORS,
  formatHistoryUsd,
  historyColumnLabel,
  type ChartPoint,
  type PriceHistoryField,
} from "../lib/priceHistory";
import {
  computeChartDomain,
  formatChartAxisUsd,
  nearestPointIndex,
  pointX,
  valueToY,
  yAxisTickValues,
} from "../lib/priceHistoryChart";

interface PriceHistoryChartProps {
  points: ChartPoint[];
  fields: PriceHistoryField[];
}

interface SeriesLine {
  key: PriceHistoryField;
  label: string;
  color: string;
}

const PLOT_WIDTH = 640;
const PLOT_HEIGHT = 180;

function buildSeries(
  points: ChartPoint[],
  fields: PriceHistoryField[],
): SeriesLine[] {
  return fields
    .filter((field) => points.some((point) => point.values[field] !== null))
    .map((field) => ({
      key: field,
      label: historyColumnLabel(field),
      color: CHART_SERIES_COLORS[field],
    }));
}

function linePath(
  points: ChartPoint[],
  field: PriceHistoryField,
  width: number,
  height: number,
  min: number,
  max: number,
): string {
  const segments: string[] = [];
  let started = false;
  points.forEach((point, index) => {
    const value = point.values[field];
    if (value === null) {
      started = false;
      return;
    }
    const x = pointX(index, width, points.length);
    const y = valueToY(value, min, max, height);
    segments.push(`${started ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`);
    started = true;
  });
  return segments.join(" ");
}

function allNumericValues(
  points: ChartPoint[],
  fields: PriceHistoryField[],
): number[] {
  return points.flatMap((point) =>
    fields
      .map((field) => point.values[field])
      .filter((value): value is number => value !== null),
  );
}

export function PriceHistoryChart({ points, fields }: PriceHistoryChartProps) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [tooltipLeft, setTooltipLeft] = useState(0);

  const series = buildSeries(points, fields);
  const allValues = allNumericValues(points, fields);
  const domain = computeChartDomain(allValues);
  const ticks = yAxisTickValues(domain.min, domain.max);
  const firstAt = points[0]?.at;
  const lastAt = points[points.length - 1]?.at;
  const activePoint = activeIndex === null ? null : points[activeIndex];

  const updateHover = useCallback(
    (clientX: number) => {
      const plot = plotRef.current;
      if (!plot || points.length === 0) {
        return;
      }
      const rect = plot.getBoundingClientRect();
      const relativeX = Math.max(
        0,
        Math.min(rect.width, clientX - rect.left),
      );
      const index = nearestPointIndex(relativeX, rect.width, points.length);
      setActiveIndex(index);
      setTooltipLeft(pointX(index, rect.width, points.length));
    },
    [points.length],
  );

  const handleMouseMove = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      updateHover(event.clientX);
    },
    [updateHover],
  );

  const handleMouseLeave = useCallback(() => {
    setActiveIndex(null);
  }, []);

  if (series.length === 0) {
    return (
      <p className="muted" style={{ marginBottom: "1rem" }}>
        No numeric pricing history (variable or free pricing only).
      </p>
    );
  }

  const hoverX =
    activeIndex === null
      ? null
      : pointX(activeIndex, PLOT_WIDTH, points.length);

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

      <div className="price-chart__plot-wrap">
        <div className="price-chart__y-axis" aria-hidden="true">
          {ticks.map((tick) => (
            <span key={tick} className="price-chart__y-tick tabular-nums">
              {formatChartAxisUsd(tick)}
            </span>
          ))}
        </div>

        <div className="price-chart__plot-column">
          <div
            ref={plotRef}
            className="price-chart__interactive"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          >
            <svg
              className="price-chart__svg"
              viewBox={`0 0 ${PLOT_WIDTH} ${PLOT_HEIGHT}`}
              preserveAspectRatio="none"
              role="img"
              aria-label="Price history chart"
            >
              {ticks.map((tick) => {
                const y = valueToY(tick, domain.min, domain.max, PLOT_HEIGHT);
                return (
                  <line
                    key={tick}
                    x1={0}
                    y1={y}
                    x2={PLOT_WIDTH}
                    y2={y}
                    className="price-chart__grid"
                  />
                );
              })}
              {series.map((s) => (
                <path
                  key={s.key}
                  d={linePath(
                    points,
                    s.key,
                    PLOT_WIDTH,
                    PLOT_HEIGHT,
                    domain.min,
                    domain.max,
                  )}
                  fill="none"
                  stroke={s.color}
                  strokeWidth={2}
                  vectorEffect="non-scaling-stroke"
                />
              ))}
              {hoverX !== null ? (
                <>
                  <line
                    x1={hoverX}
                    y1={0}
                    x2={hoverX}
                    y2={PLOT_HEIGHT}
                    className="price-chart__crosshair"
                  />
                  {series.map((s) => {
                    const value = activePoint?.values[s.key];
                    if (value === null || value === undefined) {
                      return null;
                    }
                    const y = valueToY(
                      value,
                      domain.min,
                      domain.max,
                      PLOT_HEIGHT,
                    );
                    return (
                      <circle
                        key={s.key}
                        cx={hoverX}
                        cy={y}
                        r={4}
                        fill={s.color}
                        stroke="var(--surface)"
                        strokeWidth={2}
                        vectorEffect="non-scaling-stroke"
                      />
                    );
                  })}
                </>
              ) : null}
            </svg>

            {activePoint ? (
              <div
                className="price-chart__tooltip"
                style={{
                  left: `${tooltipLeft}px`,
                  transform:
                    tooltipLeft >
                    (plotRef.current?.clientWidth ?? PLOT_WIDTH) * 0.65
                      ? "translate(-100%, -0.5rem)"
                      : "translate(0.5rem, -0.5rem)",
                }}
              >
                <div className="price-chart__tooltip-date tabular-nums">
                  {activePoint.at.toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </div>
                {series.map((s) => {
                  const value = activePoint.values[s.key];
                  if (value === null) {
                    return null;
                  }
                  return (
                    <div key={s.key} className="price-chart__tooltip-row">
                      <span
                        className="price-chart__swatch"
                        style={{ backgroundColor: s.color }}
                      />
                      <span>{s.label}</span>
                      <span className="tabular-nums">
                        {formatHistoryUsd(String(value))}/M
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="price-chart__hint muted">
                Hover the chart to inspect prices
              </p>
            )}
          </div>

          <div className="price-chart__axis">
            <span>
              {firstAt?.toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              })}
            </span>
            <span className="muted">USD / 1M tokens</span>
            <span>
              {lastAt?.toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              })}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
