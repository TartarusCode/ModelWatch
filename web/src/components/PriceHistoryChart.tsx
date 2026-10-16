import { useCallback, useMemo, useRef, useState } from "react";
import {
  CHART_SERIES_COLORS,
  formatHistoryUsd,
  historyColumnLabel,
  type ChartPoint,
  type PriceHistoryField,
} from "../lib/priceHistory";
import {
  DAY_MS,
  computeChartDomain,
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
  type ChartGap,
  type TimeDomain,
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

interface RangeOption {
  key: string;
  label: string;
  title: string;
  spanMs: number | null;
}

const PLOT_WIDTH = 640;
const PLOT_HEIGHT = 180;
const DOT_LIMIT = 40;
/** Below this share of the plot width a gap band is too narrow to label inline. */
const GAP_CHIP_MIN_PCT = 8;

const RANGE_OPTIONS: RangeOption[] = [
  { key: "24h", label: "24h", title: "Last 24 hours", spanMs: DAY_MS },
  { key: "7d", label: "7d", title: "Last 7 days", spanMs: 7 * DAY_MS },
  { key: "30d", label: "1m", title: "Last 30 days", spanMs: 30 * DAY_MS },
  { key: "90d", label: "3m", title: "Last 90 days", spanMs: 90 * DAY_MS },
  { key: "all", label: "All", title: "All recorded history", spanMs: null },
];

const DEFAULT_RANGE_KEY = "all";

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
  domain: TimeDomain,
  gaps: ChartGap[],
  width: number,
  height: number,
  min: number,
  max: number,
): string {
  const gapEnds = new Set(gaps.map((gap) => gap.endIndex));
  const segments: string[] = [];
  let started = false;
  points.forEach((point, index) => {
    const value = point.values[field];
    if (value === null) {
      started = false;
      return;
    }
    const x = timeToX(point.at.getTime(), domain, width);
    const y = valueToY(value, min, max, height);
    // A gap means no snapshots were collected there: start a new subpath so the
    // line never implies an observed price across the missing period.
    const draw = !started || gapEnds.has(index);
    segments.push(`${draw ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`);
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

function shortDate(time: number): string {
  return new Date(time).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function shortDateTime(time: number): string {
  return new Date(time).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function PriceHistoryChart({ points, fields }: PriceHistoryChartProps) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [rangeKey, setRangeKey] = useState(DEFAULT_RANGE_KEY);
  const [hoverTime, setHoverTime] = useState<number | null>(null);

  const range =
    RANGE_OPTIONS.find((option) => option.key === rangeKey) ??
    RANGE_OPTIONS[RANGE_OPTIONS.length - 1];
  const windowed = useMemo(
    () => windowHistoryPoints(points, range.spanMs),
    [points, range.spanMs],
  );
  const visiblePoints = windowed.points;
  const times = useMemo(
    () => visiblePoints.map((point) => point.at.getTime()),
    [visiblePoints],
  );
  const timeDomain = useMemo(
    () =>
      resolveTimeDomain(times, windowed.windowStart, windowed.windowEnd),
    [times, windowed.windowEnd, windowed.windowStart],
  );
  const gaps = useMemo(() => detectHistoryGaps(times), [times]);

  const series = buildSeries(visiblePoints, fields);
  const domain = computeChartDomain(allNumericValues(visiblePoints, fields));
  const ticks = yAxisTickValues(domain.min, domain.max);

  const selectRange = useCallback((option: RangeOption) => {
    setRangeKey(option.key);
    setHoverTime(null);
  }, []);

  const updateHover = useCallback(
    (clientX: number) => {
      const plot = plotRef.current;
      if (!plot || times.length === 0) {
        return;
      }
      const rect = plot.getBoundingClientRect();
      const relativeX = Math.max(0, Math.min(rect.width, clientX - rect.left));
      setHoverTime(xToTime(relativeX, timeDomain, rect.width));
    },
    [timeDomain, times],
  );

  const handleMouseMove = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      updateHover(event.clientX);
    },
    [updateHover],
  );

  const handleMouseLeave = useCallback(() => {
    setHoverTime(null);
  }, []);

  const rangePicker = (
    <div
      className="price-chart__ranges"
      role="group"
      aria-label="Chart time range"
    >
      {RANGE_OPTIONS.map((option) => {
        const active = option.key === rangeKey;
        return (
          <button
            key={option.key}
            type="button"
            className={`price-chart__range${active ? " price-chart__range--active" : ""}`}
            aria-pressed={active}
            title={option.title}
            onClick={() => selectRange(option)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );

  if (buildSeries(points, fields).length === 0) {
    return (
      <p className="muted" style={{ marginBottom: "1rem" }}>
        No numeric pricing history (variable or free pricing only).
      </p>
    );
  }

  if (series.length === 0) {
    return (
      <div className="price-chart">
        <div className="price-chart__header">
          <span className="price-chart__legend-item muted">
            No snapshots in this range
          </span>
          {rangePicker}
        </div>
        <p className="price-chart__note muted">
          No price snapshots were recorded in this window — choose a wider range
          to see earlier data.
        </p>
      </div>
    );
  }

  // Hover resolves to the gap under the cursor, or to the nearest reading, which
  // the crosshair and dots snap onto.
  const hoveredGap =
    hoverTime === null ? null : gapContainingTime(gaps, hoverTime);
  const activeIndex =
    hoverTime === null || hoveredGap !== null
      ? null
      : nearestPointIndexByTime(hoverTime, times);
  const activePoint = activeIndex === null ? null : visiblePoints[activeIndex];
  const crosshairX =
    hoveredGap !== null && hoverTime !== null
      ? timeToX(hoverTime, timeDomain, PLOT_WIDTH)
      : activePoint
        ? timeToX(activePoint.at.getTime(), timeDomain, PLOT_WIDTH)
        : null;
  const plotWidthPx = plotRef.current?.clientWidth ?? PLOT_WIDTH;
  const tooltipLeft =
    ((crosshairX ?? 0) / PLOT_WIDTH) * plotWidthPx;
  const spanMs = timeDomain.end - timeDomain.start;
  const showTimeInTicks = spanMs <= 2 * DAY_MS;
  const axisTicks = timeAxisTicks(
    timeDomain,
    PLOT_WIDTH,
    showTimeInTicks ? 4 : 5,
  );
  const showDots = visiblePoints.length <= DOT_LIMIT;
  const bandX = (gap: ChartGap) => ({
    start: timeToX(gap.startAt, timeDomain, PLOT_WIDTH),
    end: timeToX(gap.endAt, timeDomain, PLOT_WIDTH),
  });
  const missingMs = totalGapDuration(gaps);
  const latestAt = points.length > 0 ? points[points.length - 1].at : null;
  const staleMs = latestAt === null ? 0 : Date.now() - latestAt.getTime();
  const staleNote =
    latestAt !== null && staleMs > 2 * DAY_MS
      ? `Latest snapshot ${shortDateTime(latestAt.getTime())} — nothing recorded for ${formatGapDuration(staleMs)} since.`
      : null;

  return (
    <div className="price-chart">
      <div className="price-chart__header">
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
        {rangePicker}
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
              aria-label={
                gaps.length > 0
                  ? `Price history chart with ${gaps.length} data collection gap${gaps.length === 1 ? "" : "s"}`
                  : "Price history chart"
              }
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
              {gaps.map((gap) => {
                const band = bandX(gap);
                return (
                  <rect
                    key={`gap-${gap.startAt}`}
                    x={band.start}
                    y={0}
                    width={Math.max(band.end - band.start, 1)}
                    height={PLOT_HEIGHT}
                    className="price-chart__gap-band"
                  />
                );
              })}
              {series.map((s) => (
                <path
                  key={s.key}
                  d={linePath(
                    visiblePoints,
                    s.key,
                    timeDomain,
                    gaps,
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
              {showDots
                ? series.flatMap((s) =>
                    visiblePoints.flatMap((point, index) => {
                      const value = point.values[s.key];
                      if (value === null) {
                        return [];
                      }
                      return (
                        <circle
                          key={`dot-${s.key}-${index}`}
                          cx={timeToX(point.at.getTime(), timeDomain, PLOT_WIDTH)}
                          cy={valueToY(value, domain.min, domain.max, PLOT_HEIGHT)}
                          r={2}
                          fill={s.color}
                        />
                      );
                    }),
                  )
                : null}
              {crosshairX !== null ? (
                <>
                  <line
                    x1={crosshairX}
                    y1={0}
                    x2={crosshairX}
                    y2={PLOT_HEIGHT}
                    className="price-chart__crosshair"
                  />
                  {activePoint
                    ? series.map((s) => {
                        const value = activePoint.values[s.key];
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
                            cx={crosshairX}
                            cy={y}
                            r={4}
                            fill={s.color}
                            stroke="var(--surface)"
                            strokeWidth={2}
                            vectorEffect="non-scaling-stroke"
                          />
                        );
                      })
                    : null}
                </>
              ) : null}
            </svg>

            {gaps.map((gap) => {
              const band = bandX(gap);
              const start = Math.max(0, band.start);
              const end = Math.min(PLOT_WIDTH, band.end);
              if (((end - start) / PLOT_WIDTH) * 100 < GAP_CHIP_MIN_PCT) {
                return null;
              }
              const centerPct = ((start + end) / 2 / PLOT_WIDTH) * 100;
              // Keep the chip inside the plot when the band hugs an edge.
              const transform =
                centerPct > 80
                  ? "translateX(-100%)"
                  : centerPct < 20
                    ? "translateX(0)"
                    : "translateX(-50%)";
              return (
                <span
                  key={`chip-${gap.startAt}`}
                  className="price-chart__gap-chip"
                  style={{ left: `${centerPct}%`, transform }}
                >
                  {formatGapDuration(gap.durationMs)} no data
                </span>
              );
            })}

            {hoveredGap ? (
              <div
                className="price-chart__tooltip price-chart__tooltip--gap"
                style={{
                  left: `${tooltipLeft}px`,
                  transform:
                    tooltipLeft > plotWidthPx * 0.65
                      ? "translate(-100%, -0.5rem)"
                      : "translate(0.5rem, -0.5rem)",
                }}
              >
                <div className="price-chart__tooltip-date">No data collected</div>
                <div className="price-chart__tooltip-row">
                  <span />
                  <span>Last reading</span>
                  <span className="tabular-nums">
                    {shortDateTime(hoveredGap.startAt)}
                  </span>
                </div>
                <div className="price-chart__tooltip-row">
                  <span />
                  <span>Next reading</span>
                  <span className="tabular-nums">
                    {shortDateTime(hoveredGap.endAt)}
                  </span>
                </div>
                <div className="price-chart__tooltip-row">
                  <span />
                  <span>{formatGapDuration(hoveredGap.durationMs)} gap</span>
                  <span />
                </div>
              </div>
            ) : activePoint ? (
              <div
                className="price-chart__tooltip"
                style={{
                  left: `${tooltipLeft}px`,
                  transform:
                    tooltipLeft > plotWidthPx * 0.65
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
                        {formatHistoryUsd(String(value), s.key)}
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
            {axisTicks.map((tick, index) => (
              <span
                key={tick.time}
                className="price-chart__axis-tick tabular-nums"
                style={{
                  textAlign:
                    index === 0
                      ? "left"
                      : index === axisTicks.length - 1
                        ? "right"
                        : "center",
                }}
              >
                {showTimeInTicks
                  ? shortDateTime(tick.time)
                  : shortDate(tick.time)}
              </span>
            ))}
          </div>
        </div>
      </div>

      <p className="price-chart__note muted">
        USD / 1M tokens · {visiblePoints.length} snapshot
        {visiblePoints.length === 1 ? "" : "s"} in view
        {windowed.carryIn
          ? " (plus the previous reading, kept to anchor the line)"
          : ""}
        {gaps.length > 0
          ? ` · ${gaps.length} collection gap${gaps.length === 1 ? "" : "s"}, ${formatGapDuration(missingMs)} missing`
          : ""}
      </p>

      {gaps.length > 0 ? (
        <p className="price-chart__note muted">
          <span className="price-chart__gap-dot" aria-hidden="true" />
          Shaded bands are periods with no snapshots collected: prices there are
          unknown, not unchanged, so the line stops and restarts instead of
          jumping across. Hover a band for its dates.
        </p>
      ) : null}

      {staleNote ? <p className="price-chart__note muted">{staleNote}</p> : null}
    </div>
  );
}
