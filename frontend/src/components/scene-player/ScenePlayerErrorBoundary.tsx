'use client';

import {Component, type ErrorInfo, type ReactNode} from 'react';

export class ScenePlayerErrorBoundary extends Component<{children: ReactNode}, {failed: boolean}> {
  public state = {failed: false};
  public static getDerivedStateFromError(): {failed: boolean} { return {failed: true}; }
  public componentDidCatch(_error: Error, _info: ErrorInfo): void {}
  public render(): ReactNode { return this.state.failed ? <p role="alert">Không thể xem trước (PLAYER_RENDER_ERROR)</p> : this.props.children; }
}
