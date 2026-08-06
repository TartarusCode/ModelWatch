import { PriceCell } from "./PriceCell";
import {
  effectivePricingSubtitle,
  formatCacheHitRate,
  formatUptime,
  hasProviderPricingData,
  mergeProviderRows,
  providerStatsErrors,
} from "../lib/providerStats";
import { formatPerMillionUsd, isFiniteNumber } from "../lib/pricing";
import type { ModelProviderStats } from "../types";

interface ProviderPricingPanelProps {
  providerStats: ModelProviderStats;
}

export function ProviderPricingPanel({
  providerStats,
}: ProviderPricingPanelProps) {
  if (!hasProviderPricingData(providerStats)) {
    const errors = providerStatsErrors(providerStats);
    if (errors.length === 0) {
      return null;
    }
    return (
      <section className="card card--wide">
        <h2 className="card__title">Provider pricing</h2>
        {errors.map((error) => (
          <p className="muted" key={error}>
            {error}
          </p>
        ))}
      </section>
    );
  }

  const rows = mergeProviderRows(
    providerStats.effective_pricing,
    providerStats.provider_endpoints,
  );
  if (rows.length === 0) {
    return null;
  }

  const subtitle = effectivePricingSubtitle(providerStats.effective_pricing);
  const errors = providerStatsErrors(providerStats);

  return (
    <section className="card card--wide">
      <h2 className="card__title">Provider pricing</h2>
      <p className="card__subtitle">
        {subtitle ??
          "List prices and cache-aware effective prices vary by upstream provider."}
      </p>
      {errors.map((error) => (
        <p className="muted" key={error}>
          {error}
        </p>
      ))}
      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>List prompt</th>
              <th>List completion</th>
              <th>Eff. input</th>
              <th>Eff. output</th>
              <th>Cache hit</th>
              <th>Uptime (30m)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.providerName}>
                <td>{row.providerName}</td>
                <td>
                  {row.listPrompt ? (
                    <PriceCell perToken={row.listPrompt} />
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td>
                  {row.listCompletion ? (
                    <PriceCell perToken={row.listCompletion} />
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td>
                  {isFiniteNumber(row.effectiveInputPrice) ? (
                    <span className="price-cell">
                      {formatPerMillionUsd(row.effectiveInputPrice)}
                    </span>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td>
                  {isFiniteNumber(row.effectiveOutputPrice) ? (
                    <span className="price-cell">
                      {formatPerMillionUsd(row.effectiveOutputPrice)}
                    </span>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td className="tabular-nums">
                  {formatCacheHitRate(row.cacheHitRate)}
                </td>
                <td className="tabular-nums">
                  {formatUptime(row.uptimeLast30m)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
