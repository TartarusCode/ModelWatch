import { lazy, Suspense } from "react";
import { Link, useParams } from "react-router-dom";
import { ArtificialAnalysisPanel } from "../components/ArtificialAnalysisPanel";
import { BenchmarkScoresPanel } from "../components/BenchmarkScoresPanel";
import { DesignArenaPanel } from "../components/DesignArenaPanel";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { PriceCell } from "../components/PriceCell";
import { PriceHistoryPanel } from "../components/PriceHistoryPanel";
import { ProviderBadge } from "../components/ProviderBadge";
import { ProviderPricingPanel } from "../components/ProviderPricingPanel";
import { isFreeTierModel, pricingFieldLabel, providerFromModelId } from "../lib/pricing";
import { useDocumentTitle } from "../lib/useDocumentTitle";
import type {
  EnrichedModel,
  ModelPricing,
  PriceEventRecord,
  PriceHistoryOutput,
} from "../types";

const ModelDescription = lazy(() =>
  import("../components/ModelDescription").then((module) => ({
    default: module.ModelDescription,
  })),
);

interface ModelDetailPageProps {
  models: EnrichedModel[];
  priceHistory: PriceHistoryOutput;
  priceEvents: PriceEventRecord[];
}

function pricingEntries(pricing: ModelPricing): [string, string][] {
  return Object.entries(pricing).filter(
    (entry): entry is [string, string] =>
      entry[1] !== undefined && entry[1] !== null,
  );
}

export function ModelDetailPage({
  models,
  priceHistory,
  priceEvents,
}: ModelDetailPageProps) {
  const { id } = useParams<{ id: string }>();
  const decodedId = id ? decodeURIComponent(id) : "";
  const enriched = models.find((m) => m.model.id === decodedId);
  useDocumentTitle(
    enriched ? `ModelWatch — ${enriched.model.name}` : "ModelWatch — Model",
  );

  if (!enriched) {
    return (
      <div className="page">
        <div className="empty-state">
          <h2>Model not found</h2>
          <p className="muted">This model isn’t in the latest snapshot.</p>
          <Link to="/" className="btn btn--primary">
            Back to models
          </Link>
        </div>
      </div>
    );
  }

  const { model, benchmarks, provider_stats: providerStats } = enriched;
  const benchmarkScoresStatus = benchmarks.benchmark_scores_status ?? {
    status: "empty" as const,
  };
  const resolvedProviderStats = providerStats ?? {
    effective_pricing: null,
    effective_pricing_status: { status: "empty" as const },
    provider_endpoints: [],
    provider_endpoints_status: { status: "empty" as const },
  };
  const provider = providerFromModelId(model.id);

  return (
    <div className="page">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/">Models</Link>
        <span aria-hidden>/</span>
        <span>{model.name}</span>
      </nav>

      <header className="model-hero">
        <div className="model-hero__top">
          <ProviderBadge provider={provider} />
          {isFreeTierModel(model.id, model.pricing) ? (
            <span className="status-pill status-pill--ok">Free tier</span>
          ) : null}
        </div>
        <h1 className="model-hero__title">{model.name}</h1>
        <p className="model-hero__id">{model.id}</p>
        {model.description ? (
          <Suspense fallback={null}>
            <ModelDescription text={model.description} />
          </Suspense>
        ) : null}
        <div className="model-hero__actions">
          <a
            href={`https://openrouter.ai/${model.id}`}
            target="_blank"
            rel="noreferrer"
            className="btn btn--primary"
          >
            Open on OpenRouter ↗
          </a>
        </div>
        <div className="model-hero__stats">
          <div className="hero-stat">
            <span className="hero-stat__label">Context</span>
            <span className="hero-stat__value tabular-nums">
              {model.context_length
                ? `${(model.context_length / 1000).toFixed(0)}k`
                : "—"}
            </span>
          </div>
          <div className="hero-stat">
            <span className="hero-stat__label">Prompt</span>
            <span className="hero-stat__value">
              <PriceCell perToken={model.pricing.prompt} />
            </span>
          </div>
          <div className="hero-stat">
            <span className="hero-stat__label">Completion</span>
            <span className="hero-stat__value">
              <PriceCell perToken={model.pricing.completion} />
            </span>
          </div>
          <div className="hero-stat">
            <span className="hero-stat__label">Created</span>
            <span className="hero-stat__value tabular-nums">
              {new Date(model.created * 1000).toLocaleDateString()}
            </span>
          </div>
        </div>
      </header>

      <PriceHistoryPanel
        modelId={model.id}
        history={priceHistory}
        events={priceEvents}
      />

      <div className="detail-grid">
        <section className="card">
          <h2 className="card__title">Current pricing</h2>
          <p className="card__subtitle">USD per 1M tokens</p>
          <div className="kv-list">
            {pricingEntries(model.pricing).map(([field, value]) => (
              <div className="kv-row" key={field}>
                <span>{pricingFieldLabel(field)}</span>
                <PriceCell perToken={value} />
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h2 className="card__title">Configuration</h2>
          <div className="kv-list">
            <div className="kv-row">
              <span>Input</span>
              <span>{model.architecture.input_modalities.join(", ") || "—"}</span>
            </div>
            <div className="kv-row">
              <span>Output</span>
              <span>{model.architecture.output_modalities.join(", ") || "—"}</span>
            </div>
            <div className="kv-row">
              <span>Moderated</span>
              <span>{model.top_provider.is_moderated ? "Yes" : "No"}</span>
            </div>
            <div className="kv-row">
              <span>Max completion</span>
              <span className="tabular-nums">
                {model.top_provider.max_completion_tokens?.toLocaleString() ??
                  "—"}
              </span>
            </div>
            {model.expiration_date ? (
              <div className="kv-row">
                <span>Expires</span>
                <span>{model.expiration_date}</span>
              </div>
            ) : null}
          </div>
          <h3 className="card__subtitle" style={{ marginTop: "1.25rem" }}>
            Parameters
          </h3>
          <div className="param-list">
            {model.supported_parameters.map((param) => (
              <span className="param-tag" key={param}>
                {param}
              </span>
            ))}
          </div>
        </section>
      </div>

      <ErrorBoundary label="Provider pricing">
        <ProviderPricingPanel providerStats={resolvedProviderStats} />
      </ErrorBoundary>

      {benchmarks.design_arena_status.status === "ok" &&
      benchmarks.design_arena ? (
        <ErrorBoundary label="Design Arena">
          <DesignArenaPanel
            records={benchmarks.design_arena.records}
            eloBounds={benchmarks.design_arena.elo_bounds}
          />
        </ErrorBoundary>
      ) : benchmarks.design_arena_status.status === "error" ? (
        <section className="card card--wide">
          <h2 className="card__title">Design Arena</h2>
          <p className="muted">
            Fetch failed: {benchmarks.design_arena_status.error ?? "unknown"}
          </p>
        </section>
      ) : null}

      <ErrorBoundary label="Benchmark scores">
        <BenchmarkScoresPanel
          records={benchmarks.benchmark_scores ?? []}
          status={benchmarkScoresStatus}
        />
      </ErrorBoundary>

      {benchmarks.artificial_analysis_status.status === "ok" ? (
        <ErrorBoundary label="Artificial Analysis">
          <ArtificialAnalysisPanel
            modelId={model.id}
            records={benchmarks.artificial_analysis}
          />
        </ErrorBoundary>
      ) : benchmarks.artificial_analysis_status.status === "error" ? (
        <section className="card card--wide">
          <h2 className="card__title">Artificial Analysis</h2>
          <p className="muted">
            Fetch failed:{" "}
            {benchmarks.artificial_analysis_status.error ?? "unknown"}
          </p>
        </section>
      ) : (
        <section className="card card--wide">
          <h2 className="card__title">Artificial Analysis</h2>
          <p className="muted">No benchmark data for this model yet.</p>
        </section>
      )}
    </div>
  );
}
