// Renders chat text as real React elements (never dangerouslySetInnerHTML) —
// ports the old vanilla JS's minimal markdown-lite (fenced code blocks,
// inline `code`, **bold**, newlines) without the XSS-shaped behavior the
// original had of trusting the AI's raw text as HTML.
let key = 0;

function renderPlainLines(text) {
  const lines = text.split('\n');
  return lines.map((line, i) => (
    <span key={key++}>{line}{i < lines.length - 1 && <br key={key++} />}</span>
  ));
}

function renderInline(text) {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part) => {
    if (!part) return null;
    if (part.length > 1 && part.startsWith('`') && part.endsWith('`')) {
      return <code key={key++}>{part.slice(1, -1)}</code>;
    }
    if (part.length > 3 && part.startsWith('**') && part.endsWith('**')) {
      return <strong key={key++}>{part.slice(2, -2)}</strong>;
    }
    return renderPlainLines(part);
  });
}

export function formatMessage(text) {
  const blocks = text.split(/(```[^\n]*\n[\s\S]*?```)/g);
  return blocks.map((block) => {
    const m = block.match(/^```[^\n]*\n([\s\S]*?)```$/);
    if (m) return <pre key={key++}><code>{m[1]}</code></pre>;
    return renderInline(block);
  });
}

export function formatPlainText(text) {
  return renderPlainLines(text);
}
