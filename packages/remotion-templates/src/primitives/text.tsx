import type {ReactNode} from 'react';

export const renderBold = (content: string, highlight = '#38BDF8'): ReactNode[] =>
  content.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) =>
    part.startsWith('**') ? <strong key={index} style={{color: highlight}}>{part.slice(2, -2)}</strong> : part,
  );

export const fittedTextStyle = (content: string, baseSize: number) => ({
  fontSize: Math.max(baseSize * 0.6, baseSize - Math.max(0, content.length - 60) * 0.35),
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap' as const,
});
