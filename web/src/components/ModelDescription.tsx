import { parseMarkdownLinks } from "../lib/markdownLinks";

interface ModelDescriptionProps {
  text: string;
}

export function ModelDescription({ text }: ModelDescriptionProps) {
  return (
    <p className="model-hero__description">{parseMarkdownLinks(text)}</p>
  );
}
