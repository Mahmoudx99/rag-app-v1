import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

function MessageRenderer({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        // Custom rendering for code blocks
        code({ node, inline, className, children, ...props }) {
          return inline ? (
            <code className="inline-code" {...props}>
              {children}
            </code>
          ) : (
            <pre className="code-block">
              <code className={className} {...props}>
                {children}
              </code>
            </pre>
          );
        },
        // Ensure links open in new tab
        a({ node, children, ...props }) {
          return (
            <a target="_blank" rel="noopener noreferrer" {...props}>
              {children}
            </a>
          );
        }
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export default MessageRenderer;
