import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import {
  formatPerMillionUsd,
  formatPct,
  pricingFieldLabel,
} from "../lib/pricing";
import type { PriceDropRecord, PriceEventRecord } from "../types";

interface DropsPageProps {
  drops: PriceDropRecord[];
  events: PriceEventRecord[];
  thresholds: { min_pct: number; min_saved_per_million_usd: number };
}

function sortDrops(drops: PriceDropRecord[]): PriceDropRecord[] {
  return [...drops].sort((a, b) => {
    if (b.pct_drop !== a.pct_drop) {
      return b.pct_drop - a.pct_drop;
    }
    return (
      Number.parseFloat(b.saved_per_million_usd) -
      Number.parseFloat(a.saved_per_million_usd)
    );
  });
}

function recentEvents(events: PriceEventRecord[]): PriceEventRecord[] {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return events
    .filter((e) => new Date(e.detected_at).getTime() >= weekAgo)
    .sort(
      (a, b) =>
        new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime(),
    );
}

export function DropsPage({ drops, events, thresholds }: DropsPageProps) {
  const sorted = sortDrops(drops);
  const recent = recentEvents(events);
  const topDrop = sorted[0];

  return (
    <div className="page">
      <PageHeader
        title="Price drops"
        description={`Significant decreases vs the previous snapshot — ≥${(thresholds.min_pct * 100).toFixed(0)}% drop and ≥$${thresholds.min_saved_per_million_usd.toFixed(2)}/M saved.`}
      />

      {topDrop ? (
        <div className="highlight-card">
          <span className="highlight-card__label">Largest recent drop</span>
          <div className="highlight-card__main">
            <Link
              to={`/models/${encodeURIComponent(topDrop.model_id)}`}
              className="highlight-card__model"
            >
              {topDrop.model_id}
            </Link>
            <span className="highlight-card__pct">
              −{formatPct(topDrop.pct_drop)}
            </span>
          </div>
          <div className="highlight-card__prices">
            <span>
              {pricingFieldLabel(topDrop.field)}:{" "}
              <s>{formatPerMillionUsd(topDrop.old_per_million_usd)}</s>
            </span>
            <span className="highlight-card__arrow">→</span>
            <span className="highlight-card__new">
              {formatPerMillionUsd(topDrop.new_per_million_usd)}
            </span>
            <span className="highlight-card__saved">
              Save {formatPerMillionUsd(topDrop.saved_per_million_usd)}/M
            </span>
          </div>
        </div>
      ) : null}

      {sorted.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state__icon" aria-hidden>
            ✓
          </span>
          <h2>No drops this cycle</h2>
          <p className="muted">
            No models crossed the significance threshold since the last
            snapshot. Check back after the next scheduled build.
          </p>
        </div>
      ) : (
        <section className="table-panel">
          <h2 className="section-title">Current snapshot</h2>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Field</th>
                  <th>Was</th>
                  <th>Now</th>
                  <th>Drop</th>
                  <th>Saved</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((drop) => (
                  <tr key={`${drop.model_id}-${drop.field}`}>
                    <td>
                      <Link
                        to={`/models/${encodeURIComponent(drop.model_id)}`}
                        className="model-cell__name"
                      >
                        {drop.model_id}
                      </Link>
                    </td>
                    <td>{pricingFieldLabel(drop.field)}</td>
                    <td>
                      <span className="price-cell price-cell--muted">
                        {formatPerMillionUsd(drop.old_per_million_usd)}
                      </span>
                    </td>
                    <td>
                      <span className="price-cell">
                        {formatPerMillionUsd(drop.new_per_million_usd)}
                      </span>
                    </td>
                    <td>
                      <span className="drop-badge">
                        −{formatPct(drop.pct_drop)}
                      </span>
                    </td>
                    <td>
                      <span className="price-cell price-cell--free">
                        {formatPerMillionUsd(drop.saved_per_million_usd)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="table-panel">
        <h2 className="section-title">Last 7 days</h2>
        {recent.length === 0 ? (
          <p className="muted">No recorded events in the last 7 days.</p>
        ) : (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Model</th>
                  <th>Field</th>
                  <th>Drop</th>
                  <th>Saved</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((event, index) => (
                  <tr key={`${event.detected_at}-${event.model_id}-${index}`}>
                    <td className="tabular-nums muted">
                      {new Date(event.detected_at).toLocaleString(undefined, {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td>
                      <Link
                        to={`/models/${encodeURIComponent(event.model_id)}`}
                        className="model-cell__name"
                      >
                        {event.model_id}
                      </Link>
                    </td>
                    <td>{pricingFieldLabel(event.field)}</td>
                    <td>
                      <span className="drop-badge">
                        −{formatPct(event.pct_drop)}
                      </span>
                    </td>
                    <td>
                      <span className="price-cell">
                        {formatPerMillionUsd(event.saved_per_million_usd)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
