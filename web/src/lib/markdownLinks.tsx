import type { ReactNode } from "react";

const MARKDOWN_LINK = /\[([^\]]+)\]\(([^)]+)\)/g;

function isSafeHref(href: string): boolean {
  try {
    const url = new URL(href);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export function parseMarkdownLinks(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(MARKDOWN_LINK)) {
    const start = match.index ?? 0;
    if (start > lastIndex) {
      parts.push(text.slice(lastIndex, start));
    }

    const label = match[1];
    const href = match[2];
    if (isSafeHref(href)) {
      parts.push(
        <a key={start} href={href} target="_blank" rel="noreferrer">
          {label}
        </a>,
      );
    } else {
      parts.push(match[0]);
    }

    lastIndex = start + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}
