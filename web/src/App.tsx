import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoadingScreen } from "./components/LoadingScreen";
import { loadSiteData } from "./lib/data";
import { newModelRecordsLast24Hours } from "./lib/newModels";
import { dropRecordsLast24Hours } from "./lib/priceDrops";
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

  const dropsLast24h = dropRecordsLast24Hours(data.priceEvents);
  const dropCount = dropsLast24h.length;
  const newModelsLast24h = newModelRecordsLast24Hours(data.newModelEvents);
  const newModelCount = newModelsLast24h.length;

  return (
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
                newModelCount={newModelCount}
                lastUpdated={data.meta.generated_at}
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
                drops={dropsLast24h}
                events={data.priceEvents}
                thresholds={data.priceDrops.thresholds}
              />
            }
          />
          <Route
            path="models/:id"
            element={
              <ModelDetailPage
                models={data.models.models}
                priceHistory={data.priceHistory}
                priceEvents={data.priceEvents}
              />
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
