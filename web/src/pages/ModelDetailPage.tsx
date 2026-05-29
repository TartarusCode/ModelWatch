import { Link, useParams } from "react-router-dom";
import { formatPerMillion, pricingFieldLabel } from "../lib/pricing";
import type { EnrichedModel, ModelPricing } from "../types";

interface ModelDetailPageProps {
  models: EnrichedModel[];
}

function pricingEntries(pricing: ModelPricing): [string, string][] {
  return Object.entries(pricing).filter(
    (entry): entry is [string, string] => entry[1] !== undefined,
  );
}

export function ModelDetailPage({ models }: ModelDetailPageProps) {
  const { id } = useParams<{ id: string }>();
  const decodedId = id ? decodeURIComponent(id) : "";
  const enriched = models.find((m) => m.model.id === decodedId);

  if (!enriched) {
    return (
      <div className="error">
        <p>Model not found.</p>
        <Link to="/">Back to models</Link>
      </div>
    );
  }

  const { model, benchmarks } = enriched;

  return (
    <div className="detail-grid">
      <div className="card" style={{ gridColumn: "1 / -1" }}>
        <h3>{model.name}</h3>
        <p className="mono muted">{model.id}</p>
        {model.description ? <p>{model.description}</p> : null}
        <p className="muted">
          Context {model.context_length?.toLocaleString() ?? "—"} · Created{" "}
          {new Date(model.created * 1000).toLocaleDateString()}
          {model.expiration_date
            ? ` · Expires ${model.expiration_date}`
            : ""}
        </p>
        <p>
          <a
            href={`https://openrouter.ai/${model.id}`}
            target="_blank"
            rel="noreferrer"
          >
            View on OpenRouter →
          </a>
        </p>
      </div>

      <div className="card">
        <h2>Pricing (per 1M tokens)</h2>
        {pricingEntries(model.pricing).map(([field, value]) => (
          <div className="pricing-row" key={field}>
            <span>{pricingFieldLabel(field)}</span>
            <span className="mono">{formatPerMillion(value)}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Configuration</h2>
        <div className="pricing-row">
          <span>Input modalities</span>
          <span>{model.architecture.input_modalities.join(", ") || "—"}</span>
        </div>
        <div className="pricing-row">
          <span>Output modalities</span>
          <span>{model.architecture.output_modalities.join(", ") || "—"}</span>
        </div>
        <div className="pricing-row">
          <span>Moderated</span>
          <span>{model.top_provider.is_moderated ? "Yes" : "No"}</span>
        </div>
        <div className="pricing-row">
          <span>Max completion</span>
          <span>
            {model.top_provider.max_completion_tokens?.toLocaleString() ?? "—"}
          </span>
        </div>
        <h2 style={{ marginTop: "1rem" }}>Supported parameters</h2>
        <div className="param-list">
          {model.supported_parameters.map((param) => (
            <span className="badge" key={param}>
              {param}
            </span>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>Design Arena</h2>
        {benchmarks.design_arena_status.status === "ok" &&
        benchmarks.design_arena ? (
          <>
            {benchmarks.design_arena.elo_bounds ? (
              <p className="muted">
                Elo range {benchmarks.design_arena.elo_bounds.min}–
                {benchmarks.design_arena.elo_bounds.max}
              </p>
            ) : null}
            <pre className="benchmark-json">
              {JSON.stringify(benchmarks.design_arena.records, null, 2)}
            </pre>
          </>
        ) : benchmarks.design_arena_status.status === "error" ? (
          <p className="muted">
            Fetch failed: {benchmarks.design_arena_status.error ?? "unknown"}
          </p>
        ) : (
          <p className="muted">No Design Arena data for this model yet.</p>
        )}
      </div>

      <div className="card">
        <h2>Artificial Analysis</h2>
        {benchmarks.artificial_analysis_status.status === "ok" ? (
          <pre className="benchmark-json">
            {JSON.stringify(benchmarks.artificial_analysis, null, 2)}
          </pre>
        ) : benchmarks.artificial_analysis_status.status === "error" ? (
          <p className="muted">
            Fetch failed:{" "}
            {benchmarks.artificial_analysis_status.error ?? "unknown"}
          </p>
        ) : (
          <p className="muted">
            No Artificial Analysis data for this model yet.
          </p>
        )}
      </div>
    </div>
  );
}
