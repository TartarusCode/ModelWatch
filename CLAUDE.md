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

Implemented in `modelwatch/price_drop_state.py` and `modelwatch/price_baselines.py`:

- **Episode state machine** per `(model_id, field)` in `data/snapshots/price-drop-state.json` with anchors that reset on recovery.
- **7-day MA** from per-model files under `web/public/data/price-history/models/` (spike-filter reference; `current < MA`). Requires **≥3 history points** in the window.
- **Settlement:** price must hold at the new level for **2 consecutive builds** before a drop episode is confirmed and appended to `price-events.jsonl`.
- **Pending cancel:** if price rises above the pending level before settlement, the pending drop is discarded (filters flash dips).
- **Thresholds:** prior-build step must meet **≥10%** and **≥$0.05/M** saved; outlier prior prices above `reference × 1.15` are ignored.
- **Recovery:** after a confirmed drop, price above `episode_start × 1.05` for **2 builds** marks the episode `recovered`, resets the anchor, and removes it from active drops.
- **Active drops invariant:** `price-drops.json` `active_drops` is derived only from live `FieldDropState.status == confirmed` in `price-drop-state.json` (`active_drops_from_state`). The `episodes` log is history-only; orphaned rows tagged `active` without a matching confirmed field state are auto-healed to `recovered` each build (`close_orphaned_active_episodes`).
- **Zero-price glitch guard** (`modelwatch/pricing_glitch.py`): paid models never alert down to $0; run `uv run python -m modelwatch.data_repair` after OpenRouter $0 glitches.
- `price-drops.json` is the **single UI source**: `active_drops`, `recovered_drops` (24h), and `episodes` (full history). Banner counts **active** drops only.
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
- Price history in `web/public/data/price-history/` — per-model JSON under `models/` (**Git LFS**); `index.json` is small and not LFS. Append on price change only; **24h heartbeat** when unchanged (keeps MA window). Up to 500 points per model. UI lazy-loads one model file on the detail page. Build job CI checkout uses `lfs: true`; test-and-lint does not.
- Detail page **Free tier** badge (`web/src/lib/pricing.ts` `isFreeTierModel`) is display-only — uses current pricing, not history; Python `is_free_tier_model` is authoritative for the build pipeline.
- First build has no price history → no price drops until enough history points accumulate (≥3 within 7 days).
- Most models return empty benchmark payloads; UI must handle `empty` status.
- **Latest aliases** (`~provider/model-latest` and `*/gpt-chat-latest`) are excluded at build time — they duplicate versioned models and skew price/benchmark stats. Historical alias rows are stripped by `uv run python -m modelwatch.data_repair`; drop/new-model windows filter them at read time.
- Benchmark APIs use **`canonical_slug`** (permaslug), not `model.id` (`:free` variants share one slug). Endpoints live under `/api/frontend/v1/private/` (not the old `/api/internal/v1/` paths).
- **Intelligence / Coding / Agentic** on OpenRouter compare come from `artificial-analysis-benchmarks` (`artificial_analysis_*_index` + `percentiles` for bar width). `frontend/stats/endpoint` is provider routing/latency stats, not AA indices.
- Build stores all AA variants in `benchmarks.artificial_analysis`; `artificial_analysis_summary` is the default profile for the overview table.
- Overview **Bench profile** column shows the default AA profile label and `+N` when more exist; links to detail. Detail page picker switches profiles.
- **CI gates:** `build-and-deploy.yml` runs `pytest`, `mypy`, and `ruff` (plus web `lint`/`test`) in a `test-and-lint` job before build/deploy.
- **Shared modules:** `modelwatch/http.py` (`auth_headers`), `modelwatch/price_parsing.py` (`parse_per_token`, `is_known_price`). `data_repair` path defaults use `path or EVENTS_PATH` at runtime (not import-time binding).
- **Frontend:** benchmark record types live in `web/src/types.ts`; Vitest smoke tests under `web/src/lib/*.test.ts`; model table uses `@tanstack/react-virtual`.
- OpenAPI lists models API auth as required; unauthenticated fetch often works but key improves reliability.
- Scheduled workflow commits data back to the default branch; ensure Actions has `contents: write`.
- **Benchmark monitoring:** `benchmark-monitoring.yml` (daily `probe`, weekly `discover` via cron-job.org); `check_build_health` gates builds when `benchmark_errors / (model_count * 4) > 0.5` (four slug-keyed sources per model). Probe slugs in `modelwatch/benchmark_health.py` — refresh from OpenRouter model/compare pages when models leave the catalog. Discovery watches browser network requests, not page HTML.

## OpenRouter stats (build-time)

Fetched in `modelwatch/fetch.py`; stored on `EnrichedModel` in `models.json`:

| Source | URL pattern | Key | Stored on |
|--------|-------------|-----|-----------|
| Artificial Analysis | `frontend/v1/private/artificial-analysis-benchmarks?slug=` | `canonical_slug` | `benchmarks.artificial_analysis` |
| Design Arena | `frontend/v1/private/design-arena-benchmarks?slug=` | `canonical_slug` | `benchmarks.design_arena` |
| Provider benchmarks | `frontend/v1/stats/benchmark-scores?permaslug=` | `canonical_slug` | `benchmarks.benchmark_scores` |
| Effective pricing | `frontend/v1/stats/effective-pricing?permaslug=&variant=standard` | `canonical_slug` | `provider_stats.effective_pricing` |
| List endpoints | `/v1/models/{author}/{slug}/endpoints` | `model.id` | `provider_stats.provider_endpoints` |

- **Effective pricing** is cache-aware observed $/M (not catalog list price). Chart time series (`inputChartData` / `outputChartData`) are not stored.
- **Benchmark scores** are per-provider routing benchmarks (GPQA, tau-bench, etc.) — distinct from AA indices.
- **List endpoints** supply catalog list prices and `uptime_last_30m`; detail page merges with effective pricing by provider name/slug.
- Build cost per run: **4 HTTP requests per unique `canonical_slug`** + **1 per `model.id`** for list endpoints (~600). Same concurrency cap as benchmarks (`DEFAULT_CONCURRENCY` in `fetch.py`).
