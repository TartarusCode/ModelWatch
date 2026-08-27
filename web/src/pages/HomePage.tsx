import { Link } from "react-router-dom";
import { NewModelBanner } from "../components/NewModelBanner";
import { PriceChangeBanner } from "../components/PriceChangeBanner";
import { ModelTable } from "../components/ModelTable";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { hasBenchmarkData } from "../lib/data";
import { useDocumentTitle } from "../lib/useDocumentTitle";
import type { EnrichedModel } from "../types";

interface HomePageProps {
  models: EnrichedModel[];
  changeCount: number;
  freshChangeCount: number;
  cutCount: number;
  hikeCount: number;
  newModelCount: number;
  recoveredCount: number;
  lastUpdated: string;
}

export function HomePage({
  models,
  changeCount,
  freshChangeCount,
  cutCount,
  hikeCount,
  newModelCount,
  recoveredCount,
  lastUpdated,
}: HomePageProps) {
  useDocumentTitle("ModelWatch — Models");
  const withBenchmarks = models.filter((m) => hasBenchmarkData(m.benchmarks)).length;
  const changeHint =
    freshChangeCount > 0
      ? `Active now · ${freshChangeCount} new today`
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
          label="Price changes"
          value={changeCount.toLocaleString()}
          hint={changeHint}
          variant={changeCount > 0 ? "success" : "default"}
          to="/changes"
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
      <PriceChangeBanner
        freshCount={freshChangeCount}
        totalCount={changeCount}
        cutCount={cutCount}
        hikeCount={hikeCount}
      />
      {recoveredCount > 0 ? (
        <p className="muted" style={{ marginBottom: "1rem" }}>
          <Link to="/changes#recovered">
            {recoveredCount} model{recoveredCount === 1 ? "" : "s"} recovered pricing
            in the last 24 hours
          </Link>
        </p>
      ) : null}
      <ModelTable models={models} />
    </div>
  );
}
