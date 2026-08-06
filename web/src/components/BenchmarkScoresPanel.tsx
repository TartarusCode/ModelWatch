import {
  formatBenchmarkScore,
  formatBenchmarkType,
  pivotBenchmarkScores,
} from "../lib/benchmarks";
import type { BenchmarkFetchStatus, BenchmarkScoreRecord } from "../types";

interface BenchmarkScoresPanelProps {
  records: BenchmarkScoreRecord[];
  status: BenchmarkFetchStatus;
}

export function BenchmarkScoresPanel({
  records,
  status,
}: BenchmarkScoresPanelProps) {
  if (status.status === "error") {
    return (
      <section className="card card--wide">
        <h2 className="card__title">Provider benchmarks</h2>
        <p className="muted">Fetch failed: {status.error ?? "unknown"}</p>
      </section>
    );
  }

  if (status.status !== "ok" || records.length === 0) {
    return null;
  }

  const { types, rows } = pivotBenchmarkScores(records);

  return (
    <section className="card card--wide">
      <h2 className="card__title">Provider benchmarks</h2>
      <p className="card__subtitle">
        Per-provider routing benchmark scores from OpenRouter stats
      </p>
      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Provider</th>
              {types.map((type) => (
                <th key={type}>{formatBenchmarkType(type)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.providerName}>
                <td>{row.providerName}</td>
                {types.map((type) => {
                  const entry = row.scores[type];
                  return (
                    <td key={type} className="tabular-nums">
                      {entry ? (
                        <>
                          {formatBenchmarkScore(entry.score)}
                          <span className="muted" style={{ display: "block" }}>
                            n={entry.runCount}
                          </span>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
