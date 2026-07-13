import type {ReactNode} from 'react';
import defaultTheme from './themes/default.json';

export type Theme = typeof defaultTheme;

export const ThemeProvider = ({children, theme = defaultTheme}: {children: ReactNode; theme?: Theme}) => (
  <div style={{backgroundColor: theme.colors.background, color: theme.colors.foreground, fontFamily: theme.font_family, height: '100%', width: '100%'}}>
    {children}
  </div>
);

export {defaultTheme};
