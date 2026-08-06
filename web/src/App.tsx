import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Layout } from "./components/Layout";
import { LoadingScreen } from "./components/LoadingScreen";
import { loadSiteData } from "./lib/data";
import { newModelRecordsLast24Hours } from "./lib/newModels";
import { sortDropsBySeverity, splitDropsByFreshness } from "./lib/priceDrops";
import { DropsPage } from "./pages/DropsPage";
import { HomePage } from "./pages/HomePage";
import { ModelDetailPage } from "./pages/ModelDetailPage";
import { NewModelsPage } from "./pages/NewModelsPage";
import type { SiteData } from "./types";

export function App() {
  const [data, setData] = useState<SiteData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSiteData()
      .then(setData)
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
      });
  }, []);

  if (error) {
    return (
      <div className="app app--centered">
        <div className="empty-state">
          <h2>Failed to load data</h2>
          <p className="muted">{error}</p>
          <p className="muted">
            Run <code className="inline-code">uv run python -m modelwatch.build</code>{" "}
            to generate files in <code className="inline-code">web/public/data/</code>.
          </p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="app app--centered">
        <LoadingScreen />
      </div>
    );
  }

  const activeDrops = sortDropsBySeverity(data.priceDrops.active_drops);
  const { freshDrops } = splitDropsByFreshness(activeDrops);
  const dropCount = activeDrops.length;
  const freshDropCount = freshDrops.length;
  const newModelsLast24h = newModelRecordsLast24Hours(data.newModelEvents);
  const newModelCount = newModelsLast24h.length;

  return (
    <ErrorBoundary label="Application">
      <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "")}>
      <Routes>
        <Route
          element={
            <Layout
              meta={data.meta}
              dropCount={dropCount}
              newModelCount={newModelCount}
            />
          }
        >
          <Route
            index
            element={
              <HomePage
                models={data.models.models}
                dropCount={dropCount}
                freshDropCount={freshDropCount}
                newModelCount={newModelCount}
                lastUpdated={data.meta.generated_at}
                recoveredCount={data.priceDrops.recovered_drops.length}
              />
            }
          />
          <Route
            path="new"
            element={
              <NewModelsPage
                models={newModelsLast24h}
                events={data.newModelEvents}
                enriched={data.models.models}
              />
            }
          />
          <Route
            path="drops"
            element={
              <DropsPage
                priceDrops={data.priceDrops}
                enriched={data.models.models}
              />
            }
          />
          <Route
            path="models/:id"
            element={
              <ModelDetailPage
                models={data.models.models}
                episodes={data.priceDrops.episodes}
              />
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </ErrorBoundary>
  );
}
