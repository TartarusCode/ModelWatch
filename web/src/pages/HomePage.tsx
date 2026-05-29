import { PriceDropBanner } from "../components/PriceDropBanner";
import { ModelTable } from "../components/ModelTable";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import type { EnrichedModel } from "../types";

interface HomePageProps {
  models: EnrichedModel[];
  dropCount: number;
  lastUpdated: string;
}

export function HomePage({ models, dropCount, lastUpdated }: HomePageProps) {
  const withBenchmarks = models.filter(
    (m) =>
      m.benchmarks.design_arena_status.status === "ok" ||
      m.benchmarks.artificial_analysis_status.status === "ok",
  ).length;

  return (
    <div className="page">
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
          label="Price drops"
          value={dropCount.toLocaleString()}
          hint="Since last build"
          variant={dropCount > 0 ? "success" : "default"}
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
      <PriceDropBanner count={dropCount} />
      <ModelTable models={models} />
    </div>
  );
}
