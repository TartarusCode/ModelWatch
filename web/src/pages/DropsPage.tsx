import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { modelDisplayName } from "../lib/modelNames";
import {
  DROP_LOOKBACK_HOURS,
  dropAgeLabel,
  sortDropsBySeverity,
  splitDropsByFreshness,
} from "../lib/priceDrops";
import {
  formatPerMillionUsd,
  formatPct,
  pricingFieldLabel,
} from "../lib/pricing";
import { useDocumentTitle } from "../lib/useDocumentTitle";
import type { EnrichedModel, PriceDropRecord, PriceDropsOutput } from "../types";

interface DropsPageProps {
  priceDrops: PriceDropsOutput;
  enriched: EnrichedModel[];
}

function DropTable({
  rows,
  enriched,
  showStatus = false,
}: {
  rows: PriceDropRecord[];
  enriched: EnrichedModel[];
  showStatus?: boolean;
}) {
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">When</th>
            <th scope="col">Age</th>
            <th scope="col">Model</th>
            <th scope="col">Field</th>
            <th scope="col">Was</th>
            <th scope="col">Now</th>
            <th scope="col">Drop</th>
            <th scope="col">Saved</th>
            {showStatus ? <th scope="col">Status</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((drop) => (
            <tr key={`${drop.detected_at}-${drop.model_id}-${drop.field}`}>
              <td className="tabular-nums muted">
                {new Date(drop.detected_at).toLocaleString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </td>
              <td>
                <span className="age-badge">{dropAgeLabel(drop)}</span>
              </td>
              <td>
                <Link
                  to={`/models/${encodeURIComponent(drop.model_id)}`}
                  className="model-cell__name"
                >
                  {modelDisplayName(drop.model_id, enriched)}
                </Link>
              </td>
              <td>{pricingFieldLabel(drop.field)}</td>
              <td>
                <span className="price-cell price-cell--muted">
                  {formatPerMillionUsd(drop.episode_start_per_million_usd)}
                </span>
              </td>
              <td>
                <span className="price-cell">
                  {formatPerMillionUsd(drop.new_per_million_usd)}
                </span>
              </td>
              <td>
                <span className="drop-badge">−{formatPct(drop.pct_drop)}</span>
              </td>
              <td>
                <span className="price-cell price-cell--free">
                  {formatPerMillionUsd(drop.saved_per_million_usd)}
                </span>
              </td>
              {showStatus ? (
                <td>
                  {drop.status === "recovered" ? (
                    <span className="status-pill status-pill--warn">
                      Recovered
                    </span>
                  ) : (
                    <span className="muted">Active</span>
                  )}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DropsPage({ priceDrops, enriched }: DropsPageProps) {
  useDocumentTitle("ModelWatch — Price drops");
  const { thresholds } = priceDrops;
  const active = sortDropsBySeverity(priceDrops.active_drops);
  const { freshDrops, olderDrops } = splitDropsByFreshness(
    active,
    DROP_LOOKBACK_HOURS,
  );
  const fresh = sortDropsBySeverity(freshDrops);
  const older = sortDropsBySeverity(olderDrops);
  const recovered = sortDropsBySeverity(priceDrops.recovered_drops);
  const history = sortDropsBySeverity(priceDrops.episodes);
  const topDrop = fresh[0] ?? active[0];

  return (
    <div className="page">
      <PageHeader
        title="Price drops"
        description={`Active drops are confirmed after ${2} consecutive builds at the new price — ≥${(thresholds.min_pct * 100).toFixed(0)}% vs the prior build and ≥$${thresholds.min_saved_per_million_usd.toFixed(2)}/M saved.`}
      />

      {topDrop ? (
        <div className="highlight-card">
          <span className="highlight-card__label">
            {fresh[0] ? "Largest new drop today" : "Largest active drop"}
          </span>
          <div className="highlight-card__main">
            <Link
              to={`/models/${encodeURIComponent(topDrop.model_id)}`}
              className="highlight-card__model"
            >
              {modelDisplayName(topDrop.model_id, enriched)}
            </Link>
            <span className="highlight-card__pct">
              −{formatPct(topDrop.pct_drop)}
            </span>
          </div>
          <div className="highlight-card__prices">
            <span>
              {pricingFieldLabel(topDrop.field)}:{" "}
              <s>{formatPerMillionUsd(topDrop.episode_start_per_million_usd)}</s>
            </span>
            <span className="highlight-card__arrow">→</span>
            <span className="highlight-card__new">
              {formatPerMillionUsd(topDrop.new_per_million_usd)}
            </span>
            <span className="highlight-card__saved">
              Save {formatPerMillionUsd(topDrop.saved_per_million_usd)}
            </span>
          </div>
        </div>
      ) : null}

      {fresh.length > 0 ? (
        <section className="table-panel">
          <h2 className="section-title">New today</h2>
          <DropTable rows={fresh} enriched={enriched} />
        </section>
      ) : null}

      <section className="table-panel">
        <h2 className="section-title">Still active</h2>
        {older.length === 0 && fresh.length === 0 ? (
          <p className="muted">No models are currently below a confirmed drop level.</p>
        ) : older.length === 0 ? (
          <p className="muted">No older active drops — all current drops are from today.</p>
        ) : (
          <DropTable rows={older} enriched={enriched} />
        )}
      </section>

      <section className="table-panel" id="recovered">
        <h2 className="section-title">
          Recently recovered ({DROP_LOOKBACK_HOURS}h)
        </h2>
        {recovered.length === 0 ? (
          <p className="muted">No recoveries in the last {DROP_LOOKBACK_HOURS} hours.</p>
        ) : (
          <DropTable rows={recovered} enriched={enriched} />
        )}
      </section>

      <section className="table-panel">
        <h2 className="section-title">Drop history</h2>
        {history.length === 0 ? (
          <p className="muted">No recorded drop episodes.</p>
        ) : (
          <DropTable rows={history} enriched={enriched} showStatus />
        )}
      </section>
    </div>
  );
}
