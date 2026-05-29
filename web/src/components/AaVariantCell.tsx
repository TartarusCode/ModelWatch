import { Link } from "react-router-dom";
import type { AaVariantInfo } from "../lib/benchmarks";

interface AaVariantCellProps {
  modelId: string;
  info: AaVariantInfo | undefined;
}

function buildTooltip(info: AaVariantInfo): string {
  const lines = [`Default: ${info.defaultName ?? info.defaultLabel ?? "unknown"}`];
  if (info.otherVariantNames.length > 0) {
    lines.push("", "Other profiles:");
    for (const name of info.otherVariantNames) {
      lines.push(`• ${name}`);
    }
  }
  lines.push("", "Open model page to switch profiles.");
  return lines.join("\n");
}

export function AaVariantCell({ modelId, info }: AaVariantCellProps) {
  if (!info?.defaultLabel) {
    return <span className="muted">—</span>;
  }

  const modelPath = `/models/${encodeURIComponent(modelId)}`;

  return (
    <Link
      to={modelPath}
      className="aa-variant-cell"
      title={buildTooltip(info)}
    >
      <span className="aa-variant-tag">{info.defaultLabel}</span>
      {info.additionalCount > 0 ? (
        <span className="aa-variant-cell__more">
          +{info.additionalCount}
        </span>
      ) : null}
    </Link>
  );
}
