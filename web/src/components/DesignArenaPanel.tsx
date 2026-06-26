import { parseDesignArenaRecords } from "../lib/benchmarks";
import type { DesignArenaRecord, EloBounds } from "../types";
import { isFiniteNumber } from "../lib/pricing";

interface DesignArenaPanelProps {
  records: DesignArenaRecord[];
  eloBounds?: EloBounds | null;
}

export function DesignArenaPanel({ records, eloBounds }: DesignArenaPanelProps) {
  const parsed = parseDesignArenaRecords(records);
  if (parsed.length === 0) {
    return null;
  }

  return (
    <section className="card card--wide">
      <h2 className="card__title">Design Arena</h2>
      {eloBounds ? (
        <p className="card__subtitle">
          Elo range {eloBounds.min}–{eloBounds.max} across categories
        </p>
      ) : (
        <p className="card__subtitle">Category-level Elo and win rates</p>
      )}
      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Arena</th>
              <th>Elo</th>
              <th>Win rate</th>
              <th>Percentile</th>
              <th>Avg time</th>
            </tr>
          </thead>
          <tbody>
            {parsed.map((record, index) => (
              <tr
                key={`${record.category}-${record.arena}-${index}`}
              >
                <td>{record.category ?? "—"}</td>
                <td className="muted">{record.arena ?? "—"}</td>
                <td className="tabular-nums">{record.elo ?? "—"}</td>
                <td className="tabular-nums">
                  {isFiniteNumber(record.win_rate)
                    ? `${record.win_rate.toFixed(1)}%`
                    : "—"}
                </td>
                <td className="tabular-nums">
                  {isFiniteNumber(record.elo_percentile)
                    ? `${record.elo_percentile}%`
                    : "—"}
                </td>
                <td className="tabular-nums muted">
                  {isFiniteNumber(record.avg_generation_time_ms)
                    ? `${(record.avg_generation_time_ms / 1000).toFixed(1)}s`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
