import { Link } from "react-router-dom";
import { NewModelBanner } from "../components/NewModelBanner";
import { PriceDropBanner } from "../components/PriceDropBanner";
import { ModelTable } from "../components/ModelTable";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { hasBenchmarkData } from "../lib/data";
import { useDocumentTitle } from "../lib/useDocumentTitle";
import type { EnrichedModel } from "../types";

interface HomePageProps {
  models: EnrichedModel[];
  dropCount: number;
  freshDropCount: number;
  newModelCount: number;
  recoveredCount: number;
  lastUpdated: string;
}

export function HomePage({
  models,
  dropCount,
  freshDropCount,
  newModelCount,
  recoveredCount,
  lastUpdated,
}: HomePageProps) {
  useDocumentTitle("ModelWatch — Models");
  const withBenchmarks = models.filter((m) => hasBenchmarkData(m.benchmarks)).length;
  const dropHint =
    freshDropCount > 0
      ? `Active now · ${freshDropCount} new today`
      : "Active now";

  return (
    <div className="page page--wide">
      <PageHeader
        title="Models"
        description="OpenRouter catalog — pricing per million tokens, context windows, and benchmark coverage."
      />
      <div className="stats-row">
        <StatCard
          label="Models"
          value={models.length.toLocaleString()}
          hint="In latest snapshot"
        />
        <StatCard
          label="With benchmarks"
          value={withBenchmarks.toLocaleString()}
          hint="Design Arena or AA"
        />
        <StatCard
          label="New models"
          value={newModelCount.toLocaleString()}
          hint="Last 24 hours"
          variant={newModelCount > 0 ? "accent" : "default"}
          to="/new"
        />
        <StatCard
          label="Price drops"
          value={dropCount.toLocaleString()}
          hint={dropHint}
          variant={dropCount > 0 ? "success" : "default"}
          to="/drops"
        />
        <StatCard
          label="Updated"
          value={new Date(lastUpdated).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
          hint={new Date(lastUpdated).toLocaleDateString()}
        />
      </div>
      <NewModelBanner count={newModelCount} />
      <PriceDropBanner freshCount={freshDropCount} totalCount={dropCount} />
      {recoveredCount > 0 ? (
        <p className="muted" style={{ marginBottom: "1rem" }}>
          <Link to="/drops#recovered">
            {recoveredCount} model{recoveredCount === 1 ? "" : "s"} recovered pricing
            in the last 24 hours
          </Link>
        </p>
      ) : null}
      <ModelTable models={models} />
    </div>
  );
}
