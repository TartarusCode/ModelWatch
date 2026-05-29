import { formatPerMillion, parseTokenPrice } from "../lib/pricing";

interface PriceCellProps {
  perToken: string;
}

export function PriceCell({ perToken }: PriceCellProps) {
  const parsed = parseTokenPrice(perToken);
  const className =
    parsed.kind === "free"
      ? "price-cell price-cell--free"
      : parsed.kind === "variable"
        ? "price-cell price-cell--varies"
        : "price-cell";
  return <span className={className}>{formatPerMillion(perToken)}</span>;
}
