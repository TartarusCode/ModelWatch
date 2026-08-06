interface ProviderBadgeProps {
  provider: string;
}

const PROVIDER_COLORS: Record<string, string> = {
  openai: "#10a37f",
  anthropic: "#d97757",
  google: "#4285f4",
  meta: "#0668e1",
  mistral: "#ff7000",
  deepseek: "#4d6bfe",
  qwen: "#624aff",
  openrouter: "#8b5cf6",
};

export function ProviderBadge({ provider }: ProviderBadgeProps) {
  const color = PROVIDER_COLORS[provider.toLowerCase()] ?? "#71717a";
  return (
    <span className="provider-badge">
      <span
        className="provider-badge__dot"
        style={{ backgroundColor: color }}
        aria-hidden
      />
      {provider}
    </span>
  );
}
