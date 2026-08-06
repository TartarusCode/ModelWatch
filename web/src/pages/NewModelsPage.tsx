import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { modelDisplayName } from "../lib/modelNames";
import {
  NEW_MODEL_LOOKBACK_HOURS,
  sortNewModelsByDetectedAt,
} from "../lib/newModels";
import { formatPerMillion } from "../lib/pricing";
import { recentEventsInDays } from "../lib/recentEvents";
import { useDocumentTitle } from "../lib/useDocumentTitle";
import type {
  EnrichedModel,
  NewModelEventRecord,
  NewModelRecord,
} from "../types";

interface NewModelsPageProps {
  models: NewModelRecord[];
  events: NewModelEventRecord[];
  enriched: EnrichedModel[];
}

function formatOpenRouterCreated(created: number): string {
  return new Date(created * 1000).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function NewModelsPage({
  models,
  events,
  enriched,
}: NewModelsPageProps) {
  useDocumentTitle("ModelWatch — New models");
  const sorted = sortNewModelsByDetectedAt(models);
  const recent = recentEventsInDays(events, 7);
  const latest = sorted[0];
  const enrichedById = new Map(
    enriched.map((entry) => [entry.model.id, entry]),
  );

  return (
    <div className="page">
      <PageHeader
        title="New models"
        description={`Models first seen on OpenRouter in the last ${NEW_MODEL_LOOKBACK_HOURS} hours (vs. the previous snapshot). Data refreshes every 30 minutes.`}
      />

      {latest ? (
        <div className="highlight-card">
          <span className="highlight-card__label">Most recent (24h)</span>
          <div className="highlight-card__main">
            <Link
              to={`/models/${encodeURIComponent(latest.model_id)}`}
              className="highlight-card__model"
            >
              {modelDisplayName(latest.model_id, enriched)}
            </Link>
          </div>
          <p className="muted highlight-card__sub">
            {latest.name} · listed {formatOpenRouterCreated(latest.created)}
          </p>
        </div>
      ) : null}

      {sorted.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state__icon" aria-hidden>
            ✓
          </span>
          <h2>No new models in the last 24 hours</h2>
          <p className="muted">
            The catalog did not gain any models since the previous build. The
            next scheduled build runs every 30 minutes.
          </p>
        </div>
      ) : (
        <section className="table-panel">
          <h2 className="section-title">Last 24 hours</h2>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Model</th>
                  <th>Name</th>
                  <th>Prompt</th>
                  <th>Context</th>
                  <th>Listed</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((entry) => {
                  const detail = enrichedById.get(entry.model_id);
                  return (
                    <tr
                      key={`${entry.detected_at ?? ""}-${entry.model_id}`}
                    >
                      <td className="tabular-nums muted">
                        {entry.detected_at
                          ? new Date(entry.detected_at).toLocaleString(
                              undefined,
                              {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              },
                            )
                          : "—"}
                      </td>
                      <td>
                        <Link
                          to={`/models/${encodeURIComponent(entry.model_id)}`}
                          className="model-cell__name"
                        >
                          {modelDisplayName(entry.model_id, enriched)}
                        </Link>
                      </td>
                      <td>{entry.name}</td>
                      <td>
                        {detail ? (
                          <span className="price-cell">
                            {formatPerMillion(detail.model.pricing.prompt)}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="tabular-nums">
                        {detail?.model.context_length?.toLocaleString() ??
                          "—"}
                      </td>
                      <td className="tabular-nums muted">
                        {formatOpenRouterCreated(entry.created)}
                      </td>
                    </tr>
                  );
                })}
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
                  <th>Name</th>
                  <th>Listed</th>
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
                        {modelDisplayName(event.model_id, enriched)}
                      </Link>
                    </td>
                    <td>{event.name}</td>
                    <td className="tabular-nums muted">
                      {formatOpenRouterCreated(event.created)}
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
