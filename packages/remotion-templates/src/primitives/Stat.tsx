import {fittedTextStyle} from './text';

export const Stat = ({value, suffix, label, highlightColor}: {
  value: string;
  suffix?: string | null;
  label?: string | null;
  highlightColor?: string | null;
}) => (
  <div style={{textAlign: 'center'}}>
    <span
      style={{
        ...fittedTextStyle(value + (suffix ?? ''), 120),
        fontWeight: 800,
        color: highlightColor ?? undefined,
        lineHeight: 1.1,
      }}
    >
      {value}
      {suffix ? <span style={{fontSize: '0.5em', fontWeight: 400}}>{suffix}</span> : null}
    </span>
    {label ? <p style={{margin: '0.3em 0 0', fontSize: 28, opacity: 0.75}}>{label}</p> : null}
  </div>
);
