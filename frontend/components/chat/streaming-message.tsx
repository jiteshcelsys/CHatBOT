"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { TypingIndicator } from "./typing-indicator";

interface Props {
  content: string;
  isStreaming?: boolean;
}

export function StreamingMessage({ content, isStreaming }: Props) {
  if (isStreaming && !content) return <TypingIndicator />;

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none break-words">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const isBlock = !!(props as { inline?: boolean }).inline === false && match;
            return isBlock ? (
              <SyntaxHighlighter
                style={oneDark as Record<string, React.CSSProperties>}
                language={match![1]}
                PreTag="div"
                className="rounded-lg text-sm"
              >
                {String(children).replace(/\n$/, "")}
              </SyntaxHighlighter>
            ) : (
              <code className="bg-muted px-1 py-0.5 rounded text-sm font-mono" {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && (
        <span className="inline-block w-0.5 h-4 bg-foreground animate-pulse ml-0.5 align-text-bottom" />
      )}
    </div>
  );
}
