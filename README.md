# ModelWatch

Unofficial [OpenRouter](https://openrouter.ai) dashboard: model pricing, configuration, and benchmark snapshots on GitHub Pages.

Repository: [github.com/TartarusCode/ModelWatch](https://github.com/TartarusCode/ModelWatch)

Live site (after enabling Pages): [tartaruscode.github.io/ModelWatch](https://tartaruscode.github.io/ModelWatch/)

## Features

- Browse 300+ models with prompt/completion pricing in **$/1M tokens**
- Filter by provider, context length, tools, reasoning, benchmark availability
- Model detail pages with full pricing, parameters, Design Arena and Artificial Analysis data
- **Price drops**: highlights decreases ≥10% with ≥$0.05/M saved vs the previous snapshot
- 7-day price event history from scheduled rebuilds

## Data sources

| Endpoint | Purpose |
|----------|---------|
| `GET https://openrouter.ai/api/v1/models` | Pricing, config, capabilities |
| `GET https://openrouter.ai/api/internal/v1/design-arena-benchmarks?slug={id}` | Design Arena benchmarks |
| `GET https://openrouter.ai/api/internal/v1/artificial-analysis-benchmarks?slug={id}` | Artificial Analysis benchmarks |

Data is fetched at **build time** (every ~30 minutes via [cron-job.org → GitHub Actions](docs/cron-job-org.md)), not in the browser.

## Local development

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Node.js 22+

### Refresh data

```powershell
uv sync
uv run python -m modelwatch.build
```

Optional: set `OPENROUTER_API_KEY` for authenticated API access.

### Run the SPA

```powershell
cd web
npm install
npm run dev
```

Open the dev server URL (Vite serves under `/ModelWatch/`).

### Tests

```powershell
uv sync --extra dev
uv run pytest
```

## GitHub Pages setup

1. Clone or push to [TartarusCode/ModelWatch](https://github.com/TartarusCode/ModelWatch) (repo name must stay `ModelWatch` for the configured Pages base path, or update `base` in `web/vite.config.ts`).
2. **Settings → Pages → Build and deployment → GitHub Actions**.
3. Optionally add repository secret `OPENROUTER_API_KEY`.
4. Configure [external cron (cron-job.org)](docs/cron-job-org.md) or run the **Build and deploy** workflow manually.

The workflow:

1. Fetches OpenRouter data and commits updates to `web/public/data/` and `data/snapshots/previous.json`
2. Builds the Vite app and deploys `web/dist` to GitHub Pages

## Project layout

```
modelwatch/          Python fetch + price-diff pipeline
web/                 Vite + React SPA
data/snapshots/      Previous pricing snapshot for diffs
.github/workflows/   workflow_dispatch build + deploy (cron via cron-job.org)
docs/                Setup guides (external cron)
```

## Disclaimer

This is not affiliated with or endorsed by OpenRouter. Benchmark and pricing data may be incomplete or delayed. Use [openrouter.ai](https://openrouter.ai) for authoritative information.

## License

MIT
