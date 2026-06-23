import ReactMarkdown from "react-markdown";

interface ModelDescriptionProps {
  text: string;
}

export function ModelDescription({ text }: ModelDescriptionProps) {
  return (
    <div className="model-hero__description">
      <ReactMarkdown
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
