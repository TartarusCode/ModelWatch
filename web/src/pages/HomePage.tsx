import { PriceDropBanner } from "../components/PriceDropBanner";
import { ModelTable } from "../components/ModelTable";
import type { EnrichedModel } from "../types";

interface HomePageProps {
  models: EnrichedModel[];
  dropCount: number;
}

export function HomePage({ models, dropCount }: HomePageProps) {
  return (
    <>
      <PriceDropBanner count={dropCount} />
      <ModelTable models={models} />
    </>
  );
}
