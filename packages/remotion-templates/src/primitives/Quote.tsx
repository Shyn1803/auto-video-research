import {renderBold} from './text';

export const Quote = ({author, content}: {
  author?: string | null;
  content: string;
}) => (
  <div style={{textAlign: 'center', maxWidth: '90%'}}>
    <p
      style={{
        fontSize: 48,
        fontWeight: 700,
        lineHeight: 1.3,
        margin: '0 0 1em',
        fontStyle: 'italic',
        position: 'relative',
      }}
    >
      <span
        style={{
          position: 'absolute',
          left: '-0.5em',
          top: '-0.3em',
          fontSize: 80,
          opacity: 0.25,
          fontStyle: 'normal',
          lineHeight: 1,
        }}
      >
        &ldquo;
      </span>
      {renderBold(content)}
    </p>
    {author ? (
      <p style={{fontSize: 22, opacity: 0.6, margin: 0}}>&mdash; {author}</p>
    ) : null}
  </div>
);
