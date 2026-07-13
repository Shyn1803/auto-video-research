import {renderBold} from './text';

export const Bullet = ({points, highlightColor}: {
  points: Array<{text: string}>;
  highlightColor?: string | null;
}) => (
  <ul style={{margin: 0, paddingLeft: '1.5em', lineHeight: 1.6}}>
    {points.map((point, i) => (
      <li key={i} style={{marginBottom: 8}}>
        {renderBold(point.text, highlightColor ?? undefined)}
      </li>
    ))}
  </ul>
);
