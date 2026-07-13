import {fittedTextStyle, renderBold} from './text';

export const Body = ({content, highlightColor}: {content: string; highlightColor?: string | null}) => (
  <p style={{...fittedTextStyle(content, 44), margin: 0}}>{renderBold(content, highlightColor ?? undefined)}</p>
);
