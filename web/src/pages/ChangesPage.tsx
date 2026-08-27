import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { modelDisplayName } from "../lib/modelNames";
import {
  CHANGE_LOOKBACK_HOURS,
  changeAgeLabel,
  countChangesByDirection,
  filterChangesByDirection,
  sortChangesBySeverity,
  sortChangesChronologically,
  splitChangesByFreshness,
  type ChangeDirectionFilter,
} from "../lib/priceChanges";
import {
  formatPerMillionUsd,
  formatSignedPct,
  formatSignedPerMillionUsd,
  pricingFieldLabel,
} from "../lib/pricing";
import { useDocumentTitle } from "../lib/useDocumentTitle";
import type {
  EnrichedModel,
  PriceChangeRecord,
  PriceChangesOutput,
} from "../types";

interface ChangesPageProps {
  priceChanges: PriceChangesOutput;
  enriched: EnrichedModel[];
}

function ChangeTable({
  rows,
  enriched,
  showStatus = false,
}: {
  rows: PriceChangeRecord[];
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
            <th scope="col">Dir</th>
            <th scope="col">Was</th>
            <th scope="col">Now</th>
            <th scope="col">Change</th>
            <th scope="col">Delta</th>
            {showStatus ? <th scope="col">Status</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((change) => (
            <tr key={`${change.detected_at}-${change.model_id}-${change.field}`}>
              <td className="tabular-nums muted">
                {new Date(change.detected_at).toLocaleString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </td>
              <td>
                <span className="age-badge">{changeAgeLabel(change)}</span>
              </td>
              <td>
                <Link
                  to={`/models/${encodeURIComponent(change.model_id)}`}
                  className="model-cell__name"
                >
                  {modelDisplayName(change.model_id, enriched)}
                </Link>
              </td>
              <td>{pricingFieldLabel(change.field)}</td>
              <td>
                <span
                  className={`change-badge change-badge--${change.direction}`}
                >
                  {change.direction === "cut" ? "Cut" : "Hike"}
                </span>
              </td>
              <td>
                <span className="price-cell price-cell--muted">
                  {formatPerMillionUsd(change.episode_start_per_million_usd)}
                </span>
              </td>
              <td>
                <span className="price-cell">
                  {formatPerMillionUsd(change.new_per_million_usd)}
                </span>
              </td>
              <td>
                <span
                  className={`change-badge change-badge--${change.direction}`}
                >
                  {formatSignedPct(change.pct_change)}
                </span>
              </td>
              <td>
                <span
                  className={`price-cell${
                    change.direction === "cut" ? " price-cell--free" : ""
                  }`}
                >
                  {formatSignedPerMillionUsd(change.delta_per_million_usd)}
                </span>
              </td>
              {showStatus ? (
                <td>
                  {change.status === "recovered" ? (
                    <span className="status-pill status-pill--warn">
                      Recovered
                    </span>
                  ) : change.status === "settled" ? (
                    <span className="status-pill status-pill--muted">
                      Settled
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

const FILTERS: { id: ChangeDirectionFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "cut", label: "Cuts" },
  { id: "hike", label: "Hikes" },
];

export function ChangesPage({ priceChanges, enriched }: ChangesPageProps) {
  useDocumentTitle("ModelWatch — Price changes");
  const [directionFilter, setDirectionFilter] =
    useState<ChangeDirectionFilter>("all");
  const { thresholds } = priceChanges;
  const activeFiltered = filterChangesByDirection(
    priceChanges.active_changes,
    directionFilter,
  );
  const activeBySeverity = sortChangesBySeverity(activeFiltered);
  const { freshChanges, olderChanges } = splitChangesByFreshness(
    activeFiltered,
    CHANGE_LOOKBACK_HOURS,
  );
  const fresh = sortChangesChronologically(freshChanges);
  const older = sortChangesChronologically(olderChanges);
  const recovered = sortChangesChronologically(
    filterChangesByDirection(priceChanges.recovered_changes, directionFilter),
    "recovered_at",
  );
  const settled = sortChangesChronologically(
    filterChangesByDirection(priceChanges.settled_changes ?? [], directionFilter),
    "settled_at",
  );
  const history = sortChangesChronologically(
    filterChangesByDirection(priceChanges.episodes, directionFilter),
  );
  const topChange =
    sortChangesBySeverity(freshChanges)[0] ?? activeBySeverity[0];
  const { cuts, hikes } = countChangesByDirection(priceChanges.active_changes);

  return (
    <div className="page">
      <PageHeader
        title="Price changes"
        description={`Confirmed after ${2} consecutive builds at the new price — ≥${(thresholds.min_pct * 100).toFixed(0)}% vs the prior build and ≥$${thresholds.min_delta_per_million_usd.toFixed(2)}/M magnitude. Changes that hold for 7 days without recovery settle as the new normal.`}
      >
        <div className="filter-chip-row" role="group" aria-label="Direction filter">
          {FILTERS.map((filter) => (
            <button
              key={filter.id}
              type="button"
              className={`filter-chip${
                directionFilter === filter.id ? " filter-chip--active" : ""
              }`}
              onClick={() => setDirectionFilter(filter.id)}
            >
              {filter.label}
              {filter.id === "cut" && cuts > 0 ? ` (${cuts})` : null}
              {filter.id === "hike" && hikes > 0 ? ` (${hikes})` : null}
            </button>
          ))}
        </div>
      </PageHeader>

      {topChange ? (
        <div
          className={`highlight-card highlight-card--${topChange.direction}`}
        >
          <span className="highlight-card__label">
            {freshChanges.length > 0
              ? "Largest change today"
              : "Largest active change"}
          </span>
          <div className="highlight-card__main">
            <Link
              to={`/models/${encodeURIComponent(topChange.model_id)}`}
              className="highlight-card__model"
            >
              {modelDisplayName(topChange.model_id, enriched)}
            </Link>
            <span
              className={`highlight-card__pct highlight-card__pct--${topChange.direction}`}
            >
              {formatSignedPct(topChange.pct_change)}
            </span>
          </div>
          <div className="highlight-card__prices">
            <span>
              {pricingFieldLabel(topChange.field)}:{" "}
              <s>
                {formatPerMillionUsd(topChange.episode_start_per_million_usd)}
              </s>
            </span>
            <span className="highlight-card__arrow">→</span>
            <span className="highlight-card__new">
              {formatPerMillionUsd(topChange.new_per_million_usd)}
            </span>
            <span
              className={`highlight-card__delta highlight-card__delta--${topChange.direction}`}
            >
              {formatSignedPerMillionUsd(topChange.delta_per_million_usd)}
            </span>
          </div>
        </div>
      ) : null}

      {fresh.length > 0 ? (
        <section className="table-panel">
          <h2 className="section-title">New today</h2>
          <ChangeTable rows={fresh} enriched={enriched} />
        </section>
      ) : null}

      <section className="table-panel">
        <h2 className="section-title">Still active</h2>
        {older.length === 0 && fresh.length === 0 ? (
          <p className="muted">
            No models currently hold a confirmed price change
            {directionFilter !== "all" ? ` (${directionFilter}s)` : ""}.
          </p>
        ) : older.length === 0 ? (
          <p className="muted">
            No older active changes — all current changes are from today.
          </p>
        ) : (
          <ChangeTable rows={older} enriched={enriched} />
        )}
      </section>

      <section className="table-panel" id="recovered">
        <h2 className="section-title">
          Recently recovered ({CHANGE_LOOKBACK_HOURS}h)
        </h2>
        {recovered.length === 0 ? (
          <p className="muted">
            No recoveries in the last {CHANGE_LOOKBACK_HOURS} hours.
          </p>
        ) : (
          <ChangeTable rows={recovered} enriched={enriched} />
        )}
      </section>

      {settled.length > 0 ? (
        <section className="table-panel" id="settled">
          <h2 className="section-title">
            Recently settled ({CHANGE_LOOKBACK_HOURS}h)
          </h2>
          <ChangeTable rows={settled} enriched={enriched} />
        </section>
      ) : null}

      <section className="table-panel">
        <h2 className="section-title">Change history</h2>
        {history.length === 0 ? (
          <p className="muted">No recorded price-change episodes.</p>
        ) : (
          <ChangeTable rows={history} enriched={enriched} showStatus />
        )}
      </section>
    </div>
  );
}
