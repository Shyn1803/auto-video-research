export const TableData = ({colA, colB, rows, highlightColor}: {
  colA: string;
  colB: string;
  rows: Array<{a: string; b: string}>;
  highlightColor?: string | null;
}) => (
  <table
    style={{
      width: '100%',
      borderCollapse: 'collapse',
      fontSize: 24,
    }}
  >
    <thead>
      <tr>
        <th style={{textAlign: 'left', padding: '8px 12px', borderBottom: '2px solid rgba(255,255,255,0.3)'}}>
          {colA}
        </th>
        <th
          style={{
            textAlign: 'right',
            padding: '8px 12px',
            borderBottom: `2px solid ${highlightColor ?? 'rgba(255,255,255,0.3)'}`,
          }}
        >
          {colB}
        </th>
      </tr>
    </thead>
    <tbody>
      {rows.map((row, i) => (
        <tr key={i}>
          <td style={{padding: '10px 12px', borderBottom: '1px solid rgba(255,255,255,0.08)'}}>{row.a}</td>
          <td
            style={{
              textAlign: 'right',
              padding: '10px 12px',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
              fontWeight: 700,
              color: highlightColor ?? undefined,
            }}
          >
            {row.b}
          </td>
        </tr>
      ))}
    </tbody>
  </table>
);
