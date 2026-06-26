import { useEffect, useMemo, useState } from "react";
import {
  loadModelAaVariant,
  resolveAaRecord,
  saveModelAaVariant,
  type ModelAaVariantSelection,
} from "../lib/aaVariants";
import {
  formatAaMetricLabel,
  formatMetricValue,
  isFiniteNumber,
  parseArtificialAnalysisRecords,
  type ArtificialAnalysisRecord,
} from "../lib/benchmarks";
import { ModelAaVariantPicker } from "./ModelAaVariantPicker";

interface ArtificialAnalysisPanelProps {
  modelId: string;
  records: Record<string, unknown>[];
}

function IndexCard({
  label,
  value,
  percentile,
}: {
  label: string;
  value: number | null | undefined;
  percentile: number | null | undefined;
}) {
  if (!isFiniteNumber(value)) {
    return null;
  }
  return (
    <div className="index-card">
      <span className="index-card__label">{label}</span>
      <span className="index-card__value tabular-nums">{value.toFixed(1)}</span>
      {isFiniteNumber(percentile) ? (
        <div className="index-card__bar">
          <div
            className="index-card__fill"
            style={{ width: `${Math.min(100, percentile)}%` }}
          />
        </div>
      ) : null}
      {isFiniteNumber(percentile) ? (
        <span className="index-card__pct muted">{percentile}th percentile</span>
      ) : null}
    </div>
  );
}

function VariantCard({
  record,
  highlighted,
}: {
  record: ArtificialAnalysisRecord;
  highlighted?: boolean;
}) {
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
    <article
      className={
        highlighted ? "aa-variant aa-variant--selected" : "aa-variant"
      }
    >
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
            isFiniteNumber(value) ? (
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

export function ArtificialAnalysisPanel({
  modelId,
  records,
}: ArtificialAnalysisPanelProps) {
  const parsed = useMemo(
    () => parseArtificialAnalysisRecords(records),
    [records],
  );
  const [selection, setSelection] = useState<ModelAaVariantSelection>(() =>
    loadModelAaVariant(modelId),
  );
  const [showAllVariants, setShowAllVariants] = useState(false);

  useEffect(() => {
    setSelection(loadModelAaVariant(modelId));
    setShowAllVariants(false);
  }, [modelId]);

  useEffect(() => {
    saveModelAaVariant(modelId, selection);
  }, [modelId, selection]);

  const selectedRecord = useMemo(
    () => resolveAaRecord(parsed, modelId, selection),
    [parsed, modelId, selection],
  );

  if (parsed.length === 0) {
    return null;
  }

  const otherVariants = parsed.filter((record) => record !== selectedRecord);

  return (
    <section className="card card--wide">
      <div className="aa-panel__header">
        <div>
          <h2 className="card__title">Artificial Analysis</h2>
          <p className="card__subtitle">
            Intelligence, coding, and agentic indices with benchmark breakdowns
          </p>
        </div>
        <ModelAaVariantPicker
          modelId={modelId}
          records={parsed}
          value={selection}
          onChange={setSelection}
        />
      </div>
      {selectedRecord ? (
        <VariantCard record={selectedRecord} highlighted />
      ) : null}
      {otherVariants.length > 0 ? (
        <div className="aa-panel__footer">
          <button
            type="button"
            className="filter-clear"
            onClick={() => setShowAllVariants((open) => !open)}
          >
            {showAllVariants
              ? "Hide other profiles"
              : `Compare all profiles (${parsed.length})`}
          </button>
        </div>
      ) : null}
      {showAllVariants ? (
        <div className="aa-variants">
          {parsed.map((record) => (
            <VariantCard
              key={record.aa_id ?? record.aa_slug}
              record={record}
              highlighted={record === selectedRecord}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
