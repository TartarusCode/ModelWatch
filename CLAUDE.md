# ModelWatch — agent notes

## Architecture

- **Python (`modelwatch/`)**: CI/cron fetches OpenRouter APIs, diffs pricing vs `data/snapshots/previous.json`, writes `web/public/data/*.json`.
- **React SPA (`web/`)**: Static site; loads JSON at runtime from `public/data/`. No live OpenRouter calls in the browser (internal benchmark URLs are not CORS-safe).

## Commands

```powershell
uv sync --extra dev
uv run pytest
uv run python -m modelwatch.build

CI: `setup-uv` caches the uv package cache (`enable-cache`, `prune-cache: false`); invalidates on `uv.lock` / `pyproject.toml`. Uses system Python on `ubuntu-latest` (not `cache-python`). Build uses `uv sync --frozen --no-dev`.

cd web
npm install
npm run dev
npm run build
```

## Price-drop rules

Implemented in `modelwatch/pricing.py`:

- Compare shared pricing fields between snapshots.
- Significant when **≥10%** drop **and** **≥$0.05/M** saved (USD per 1M tokens).
- Events append to `web/public/data/price-events.jsonl` (max 500 lines).
- `price-drops.json` lists drops from the last **24 hours** of events (30m builds); UI counts/banner match that window.
- JSON artifacts use `modelwatch.json_output` (`sort_keys=True` at every object level) for stable git diffs.

## New-model tracking

Implemented in `modelwatch/new_models.py`:

- Compare current snapshot IDs to `data/snapshots/previous.json`; any new `model.id` is an addition.
- Events append to `web/public/data/new-model-events.jsonl` (max 500 lines).
- `new-models.json` lists additions from the last **24 hours** of events; UI stat card, banner, and `/new` page match that window.
- First build has no `previous.json` → no new-model events until the second run.

## GitHub Pages

- Repo: https://github.com/TartarusCode/ModelWatch
- Site: https://tartaruscode.github.io/ModelWatch/
- Vite `base` is `/ModelWatch/` — change in `web/vite.config.ts` if the repo is renamed.
- SPA deep links: `web/public/404.html` + redirect snippet in `index.html` (rafgraph/spa-github-pages) so `/drops` and `/new` reload work on GitHub Pages.
- Enable Pages: **Settings → Pages → Source: GitHub Actions**.
- Optional secret: `OPENROUTER_API_KEY` for authenticated models API calls.

## Gotchas

- OpenRouter uses per-token price `-1` for routers/variable pricing (e.g. `openrouter/auto`). Treat as "Varies", never multiply by 1M.
- Price history in `web/public/data/price-history.json` — all `PRICING_FIELDS` (prompt, completion, cache read, etc.); UI shows columns/series only for fields with data.
- First build has no `previous.json` → no price drops until the second run.
- Most models return empty benchmark payloads; UI must handle `empty` status.
- Benchmark APIs use **`canonical_slug`** (permaslug), not `model.id` (`:free` variants share one slug).
- **Intelligence / Coding / Agentic** on OpenRouter compare come from `artificial-analysis-benchmarks` (`artificial_analysis_*_index` + `percentiles` for bar width). `frontend/stats/endpoint` is provider routing/latency stats, not AA indices.
- Build stores all AA variants in `benchmarks.artificial_analysis`; `artificial_analysis_summary` is the default profile for the overview table.
- Overview **Bench profile** column shows the default AA profile label and `+N` when more exist; links to detail. Detail page picker switches profiles.
- OpenAPI lists models API auth as required; unauthenticated fetch often works but key improves reliability.
- Scheduled workflow commits data back to the default branch; ensure Actions has `contents: write`.
