# ModelWatch — agent notes

## Architecture

- **Python (`modelwatch/`)**: CI/cron fetches OpenRouter APIs, diffs pricing vs `data/snapshots/previous.json`, writes `web/public/data/*.json`.
- **React SPA (`web/`)**: Static site; loads JSON at runtime from `public/data/`. No live OpenRouter calls in the browser (internal benchmark URLs are not CORS-safe).

## Commands

```powershell
uv sync --extra dev
uv run pytest
uv run python -m modelwatch.build

# Benchmark monitoring (optional)
uv run python -m modelwatch.api_health
uv run python -m modelwatch.check_build_health
uv sync --extra discover && uv run playwright install chromium
uv run python -m modelwatch.discover_benchmark_urls

CI: `setup-uv` caches the uv package cache (`enable-cache`, `prune-cache: false`); invalidates on `uv.lock` / `pyproject.toml`. Uses system Python on `ubuntu-latest` (not `cache-python`). Build uses `uv sync --frozen --no-dev`.

cd web
npm install
npm run dev
npm run build
```

## Price-drop rules

Implemented in `modelwatch/pricing.py` and `modelwatch/price_baselines.py`:

- Compare current pricing to a **reference price** per model/field: `max(7-day moving average, ratchet baseline)`.
- **7-day MA** is computed from `web/public/data/price-history.json` (time-based window, not snapshot count — handles irregular cron cadence). Requires **≥3 history points** in the window; otherwise skip detection for that model until enough data exists.
- **Ratchet baseline** stored in `data/snapshots/price-drop-baselines.json`; updated only on confirmed drops (never raised on price increases). When a baseline exists, current price must be **strictly below** it to alert — prevents re-firing when price returns to a previously dropped level after a spike.
- Significant when **≥10%** drop below reference **and** **≥$0.05/M** saved (USD per 1M tokens).
- Events append to `web/public/data/price-events.jsonl` (max 500 lines).
- `price-drops.json` lists drops from the last **24 hours** of events (30m builds); UI counts/banner match that window.
- JSON artifacts use `modelwatch.json_output` (`sort_keys=True` at every object level) for stable git diffs.
- `modelwatch.stable_output` sorts the models list by `model.id` and orders benchmark record arrays before write — `sort_keys` does not reorder JSON arrays.

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
- Builds are dispatched every ~30 minutes by [cron-job.org](https://cron-job.org) calling `workflow_dispatch` on `.github/workflows/build-and-deploy.yml` — see [docs/cron-job-org.md](docs/cron-job-org.md). GitHub's native `schedule` cron was removed (best-effort, often only 6–7 runs/day).
- Optional secret: `OPENROUTER_API_KEY` for authenticated models API calls.

## Gotchas

- OpenRouter uses per-token price `-1` for routers/variable pricing (e.g. `openrouter/auto`). Treat as "Varies", never multiply by 1M.
- Price history in `web/public/data/price-history.json` — all `PRICING_FIELDS` (prompt, completion, cache read, etc.); one point per scheduled build per model (up to 500 points retained); UI shows columns/series only for fields with data.
- First build has no price history → no price drops until enough history points accumulate (≥3 within 7 days).
- Most models return empty benchmark payloads; UI must handle `empty` status.
- Benchmark APIs use **`canonical_slug`** (permaslug), not `model.id` (`:free` variants share one slug). Endpoints live under `/api/frontend/v1/private/` (not the old `/api/internal/v1/` paths).
- **Intelligence / Coding / Agentic** on OpenRouter compare come from `artificial-analysis-benchmarks` (`artificial_analysis_*_index` + `percentiles` for bar width). `frontend/stats/endpoint` is provider routing/latency stats, not AA indices.
- Build stores all AA variants in `benchmarks.artificial_analysis`; `artificial_analysis_summary` is the default profile for the overview table.
- Overview **Bench profile** column shows the default AA profile label and `+N` when more exist; links to detail. Detail page picker switches profiles.
- OpenAPI lists models API auth as required; unauthenticated fetch often works but key improves reliability.
- Scheduled workflow commits data back to the default branch; ensure Actions has `contents: write`.
- **Benchmark monitoring:** `benchmark-monitoring.yml` (daily `probe`, weekly `discover` via cron-job.org); `check_build_health` gates builds when `benchmark_errors / (model_count * 2) > 0.5`. Probe slugs in `modelwatch/benchmark_health.py` — refresh from OpenRouter model/compare pages when models leave the catalog. Discovery watches browser network requests, not page HTML.
