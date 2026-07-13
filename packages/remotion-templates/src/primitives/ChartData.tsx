export const ChartData = ({rows, colA, colB}: {
  rows: Array<Record<string, string | number>>;
  colA?: string | null;
  colB?: string | null;
}) => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      width: '100%',
    }}
  >
    {(colA || colB) && (
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          padding: '0 8px',
          fontSize: 20,
          fontWeight: 600,
          opacity: 0.6,
          borderBottom: '1px solid rgba(255,255,255,0.15)',
          paddingBottom: 8,
        }}
      >
        <span>{colA ?? 'A'}</span>
        <span>{colB ?? 'B'}</span>
      </div>
    )}
    {rows.map((row, i) => (
      <div
        key={i}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 8px',
          background: 'rgba(255,255,255,0.04)',
          borderRadius: 8,
        }}
      >
        <span style={{flex: 1}}>{String(row.a ?? row[colA ?? 'a'] ?? '')}</span>
        <span
          style={{
            fontWeight: 700,
            color: '#38BDF8',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {String(row.b ?? row[colB ?? 'b'] ?? '')}
        </span>
      </div>
    ))}
  </div>
);
