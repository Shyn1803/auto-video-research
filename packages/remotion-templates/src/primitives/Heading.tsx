import {fittedTextStyle, renderBold} from './text';

export const Heading = ({content, highlightColor}: {content: string; highlightColor?: string | null}) => (
  <h1 style={{...fittedTextStyle(content, 92), margin: 0, fontWeight: 800}}>{renderBold(content, highlightColor ?? undefined)}</h1>
);
