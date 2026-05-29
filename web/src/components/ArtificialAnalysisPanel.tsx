import {
  formatAaMetricLabel,
  formatMetricValue,
  parseArtificialAnalysisRecords,
  type ArtificialAnalysisRecord,
} from "../lib/benchmarks";

interface ArtificialAnalysisPanelProps {
  records: Record<string, unknown>[];
}

function IndexCard({
  label,
  value,
  percentile,
}: {
  label: string;
  value: number | undefined;
  percentile: number | undefined;
}) {
  if (value === undefined) {
    return null;
  }
  return (
    <div className="index-card">
      <span className="index-card__label">{label}</span>
      <span className="index-card__value tabular-nums">{value.toFixed(1)}</span>
      {percentile !== undefined ? (
        <div className="index-card__bar">
          <div
            className="index-card__fill"
            style={{ width: `${Math.min(100, percentile)}%` }}
          />
        </div>
      ) : null}
      {percentile !== undefined ? (
        <span className="index-card__pct muted">{percentile}th percentile</span>
      ) : null}
    </div>
  );
}

function VariantCard({ record }: { record: ArtificialAnalysisRecord }) {
  const evaluations = record.benchmark_data?.evaluations ?? {};
  const percentiles = record.percentiles ?? {};
  const coreMetrics = [
    {
      label: "Intelligence",
      value: evaluations.artificial_analysis_intelligence_index,
      percentile: percentiles.intelligence_percentile,
    },
    {
      label: "Coding",
      value: evaluations.artificial_analysis_coding_index,
      percentile: percentiles.coding_percentile,
    },
    {
      label: "Agentic",
      value: evaluations.artificial_analysis_agentic_index,
      percentile: percentiles.agentic_percentile,
    },
  ];
  const otherMetrics = Object.entries(evaluations).filter(
    ([key]) =>
      key !== "artificial_analysis_intelligence_index" &&
      key !== "artificial_analysis_coding_index" &&
      key !== "artificial_analysis_agentic_index",
  );

  return (
    <article className="aa-variant">
      <header className="aa-variant__header">
        <h3 className="aa-variant__title">{record.aa_name ?? record.aa_slug}</h3>
        {record.benchmark_data?.model_type ? (
          <span className="status-pill">{record.benchmark_data.model_type}</span>
        ) : null}
      </header>
      <div className="index-grid">
        {coreMetrics.map((metric) => (
          <IndexCard
            key={metric.label}
            label={metric.label}
            value={metric.value}
            percentile={metric.percentile}
          />
        ))}
      </div>
      {otherMetrics.length > 0 ? (
        <div className="metric-grid">
          {otherMetrics.map(([key, value]) =>
            typeof value === "number" ? (
              <div className="metric-cell" key={key}>
                <span className="metric-cell__label">
                  {formatAaMetricLabel(key)}
                </span>
                <span className="metric-cell__value tabular-nums">
                  {formatMetricValue(key, value)}
                </span>
              </div>
            ) : null,
          )}
        </div>
      ) : null}
    </article>
  );
}

export function ArtificialAnalysisPanel({ records }: ArtificialAnalysisPanelProps) {
  const parsed = parseArtificialAnalysisRecords(records);
  if (parsed.length === 0) {
    return null;
  }

  return (
    <section className="card card--wide">
      <h2 className="card__title">Artificial Analysis</h2>
      <p className="card__subtitle">
        Intelligence, coding, and agentic indices with benchmark breakdowns
      </p>
      <div className="aa-variants">
        {parsed.map((record) => (
          <VariantCard key={record.aa_id ?? record.aa_slug} record={record} />
        ))}
      </div>
    </section>
  );
}
