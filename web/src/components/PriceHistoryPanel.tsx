import {
  activeHistoryFields,
  formatHistoryUsd,
  getModelHistory,
  historyColumnLabel,
  historyPerMillionKey,
  historyToChartPoints,
} from "../lib/priceHistory";
import { episodesForModel } from "../lib/priceDrops";
import { formatPerMillionUsd, formatPct, pricingFieldLabel } from "../lib/pricing";
import type { PriceDropRecord, PriceHistoryOutput } from "../types";
import { PriceHistoryChart } from "./PriceHistoryChart";

interface PriceHistoryPanelProps {
  modelId: string;
  history: PriceHistoryOutput;
  episodes: PriceDropRecord[];
}

export function PriceHistoryPanel({
  modelId,
  history,
  episodes,
}: PriceHistoryPanelProps) {
  const points = getModelHistory(history, modelId);
  const historyFields = activeHistoryFields(points);
  const chartPoints = historyToChartPoints(points);
  const modelEpisodes = episodesForModel(episodes, modelId);

  if (points.length === 0 && modelEpisodes.length === 0) {
    return (
      <section className="card card--wide">
        <h2 className="card__title">Price history</h2>
        <p className="muted">
          History builds up after each scheduled snapshot. Check back after more
          data refreshes.
        </p>
      </section>
    );
  }

  return (
    <section className="card card--wide">
      <h2 className="card__title">Price history</h2>
      <p className="card__subtitle">USD per 1M tokens · recorded on each build</p>

      {chartPoints.length > 0 && historyFields.length > 0 ? (
        <PriceHistoryChart points={chartPoints} fields={historyFields} />
      ) : null}

      {points.length > 0 ? (
        <div className="data-table-wrap history-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Recorded</th>
                {historyFields.map((field) => (
                  <th key={field}>{historyColumnLabel(field)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...points].reverse().map((point) => (
                <tr key={point.recorded_at}>
                  <td className="tabular-nums muted">
                    {new Date(point.recorded_at).toLocaleString(undefined, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                  {historyFields.map((field) => (
                    <td key={field}>
                      <span className="price-cell">
                        {formatHistoryUsd(point[historyPerMillionKey(field)])}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {modelEpisodes.length > 0 ? (
        <>
          <h3 className="card__subtitle" style={{ marginTop: "1.25rem" }}>
            Significant drops
          </h3>
          <p className="muted" style={{ marginBottom: "0.75rem" }}>
            Confirmed episodes only; prices must hold for two builds before
            alerting.
          </p>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Field</th>
                  <th>Was</th>
                  <th>Now</th>
                  <th>Drop</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {modelEpisodes.map((episode) => (
                  <tr key={`${episode.detected_at}-${episode.field}`}>
                    <td className="tabular-nums muted">
                      {new Date(episode.detected_at).toLocaleString()}
                    </td>
                    <td>{pricingFieldLabel(episode.field)}</td>
                    <td className="price-cell price-cell--muted">
                      {formatPerMillionUsd(episode.episode_start_per_million_usd)}
                    </td>
                    <td className="price-cell">
                      {formatPerMillionUsd(episode.new_per_million_usd)}
                    </td>
                    <td>
                      <span className="drop-badge">
                        −{formatPct(episode.pct_drop)}
                      </span>
                    </td>
                    <td>
                      {episode.status === "recovered" ? (
                        <span className="status-pill status-pill--warn">
                          Recovered
                          {episode.recovered_per_million_usd
                            ? ` → ${formatPerMillionUsd(episode.recovered_per_million_usd)}`
                            : ""}
                        </span>
                      ) : (
                        <span className="muted">Active</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}
