'use client';

import {Component, type ErrorInfo, type ReactNode} from 'react';

export class ScenePlayerErrorBoundary extends Component<{children: ReactNode}, {failed: boolean}> {
  public state = {failed: false};
  public static getDerivedStateFromError(): {failed: boolean} { return {failed: true}; }
  public componentDidCatch(error: Error, info: ErrorInfo): void {
    void error;
    void info;
  }
  public render(): ReactNode { return this.state.failed ? <p role="alert">Không thể xem trước (PLAYER_RENDER_ERROR)</p> : this.props.children; }
}
