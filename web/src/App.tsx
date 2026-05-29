import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { loadSiteData } from "./lib/data";
import { DropsPage } from "./pages/DropsPage";
import { HomePage } from "./pages/HomePage";
import { ModelDetailPage } from "./pages/ModelDetailPage";
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
      <div className="app-shell error">
        <p>Failed to load data: {error}</p>
        <p className="muted">
          Run <code>uv run python -m modelwatch.build</code> to generate data
          files in web/public/data/.
        </p>
      </div>
    );
  }

  if (!data) {
    return <div className="app-shell loading">Loading model data…</div>;
  }

  const dropCount = data.priceDrops.drops.length;

  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "")}>
      <Routes>
        <Route
          element={<Layout meta={data.meta} dropCount={dropCount} />}
        >
          <Route
            index
            element={
              <HomePage models={data.models.models} dropCount={dropCount} />
            }
          />
          <Route
            path="drops"
            element={
              <DropsPage
                drops={data.priceDrops.drops}
                events={data.priceEvents}
                thresholds={data.priceDrops.thresholds}
              />
            }
          />
          <Route
            path="models/:id"
            element={<ModelDetailPage models={data.models.models} />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
