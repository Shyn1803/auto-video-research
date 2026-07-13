export const CodeBlock = ({content, language}: {
  content: string;
  language?: string | null;
}) => (
  <pre
    style={{
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      fontSize: 22,
      lineHeight: 1.5,
      background: 'rgba(0,0,0,0.35)',
      padding: '1em 1.2em',
      borderRadius: 12,
      overflowX: 'auto',
      margin: 0,
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
    }}
  >
    {language ? (
      <span
        style={{
          display: 'block',
          fontSize: 14,
          fontWeight: 600,
          opacity: 0.5,
          marginBottom: 6,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        {language}
      </span>
    ) : null}
    {content}
  </pre>
);
