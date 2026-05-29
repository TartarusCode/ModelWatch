import { Link } from "react-router-dom";
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

  return (
    <>
      <p className="muted" style={{ marginBottom: "1rem" }}>
        Significant decreases vs the previous snapshot: ≥
        {(thresholds.min_pct * 100).toFixed(0)}% drop and ≥$
        {thresholds.min_saved_per_million_usd.toFixed(2)}/M saved.
      </p>

      {sorted.length === 0 ? (
        <div className="card">
          <p>No significant price drops detected in the latest build.</p>
        </div>
      ) : (
        <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
          <table>
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
                    >
                      {drop.model_id}
                    </Link>
                  </td>
                  <td>{pricingFieldLabel(drop.field)}</td>
                  <td className="mono">
                    {formatPerMillionUsd(drop.old_per_million_usd)}
                  </td>
                  <td className="mono">
                    {formatPerMillionUsd(drop.new_per_million_usd)}
                  </td>
                  <td className="drop-pct">{formatPct(drop.pct_drop)}</td>
                  <td className="mono">
                    {formatPerMillionUsd(drop.saved_per_million_usd)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>
        Drops in the last 7 days
      </h2>
      {recent.length === 0 ? (
        <p className="muted">No recorded events in the last 7 days.</p>
      ) : (
        <div className="table-wrap">
          <table>
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
                  <td className="mono">
                    {new Date(event.detected_at).toLocaleString()}
                  </td>
                  <td>
                    <Link
                      to={`/models/${encodeURIComponent(event.model_id)}`}
                    >
                      {event.model_id}
                    </Link>
                  </td>
                  <td>{pricingFieldLabel(event.field)}</td>
                  <td className="drop-pct">{formatPct(event.pct_drop)}</td>
                  <td className="mono">
                    {formatPerMillionUsd(event.saved_per_million_usd)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
