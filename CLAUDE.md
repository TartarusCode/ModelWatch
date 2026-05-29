# ModelWatch — agent notes

## Architecture

- **Python (`modelwatch/`)**: CI/cron fetches OpenRouter APIs, diffs pricing vs `data/snapshots/previous.json`, writes `web/public/data/*.json`.
- **React SPA (`web/`)**: Static site; loads JSON at runtime from `public/data/`. No live OpenRouter calls in the browser (internal benchmark URLs are not CORS-safe).

## Commands

```powershell
uv sync --extra dev
uv run pytest
uv run python -m modelwatch.build

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

## GitHub Pages

- Repo: https://github.com/TartarusCode/ModelWatch
- Site: https://tartaruscode.github.io/ModelWatch/
- Vite `base` is `/ModelWatch/` — change in `web/vite.config.ts` if the repo is renamed.
- Enable Pages: **Settings → Pages → Source: GitHub Actions**.
- Optional secret: `OPENROUTER_API_KEY` for authenticated models API calls.

## Gotchas

- OpenRouter uses per-token price `-1` for routers/variable pricing (e.g. `openrouter/auto`). Treat as "Varies", never multiply by 1M.
- Price history in `web/public/data/price-history.json` — appends on each build when pricing changes (max 500 points/model).
- First build has no `previous.json` → no price drops until the second run.
- Most models return empty benchmark payloads; UI must handle `empty` status.
- OpenAPI lists models API auth as required; unauthenticated fetch often works but key improves reliability.
- Scheduled workflow commits data back to the default branch; ensure Actions has `contents: write`.
