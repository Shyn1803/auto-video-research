import {describe, expect, it} from 'vitest';
import {render, screen} from '@testing-library/react';

import {ScenePlayerErrorBoundary} from '../ScenePlayerErrorBoundary';

describe('ScenePlayerErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <ScenePlayerErrorBoundary>
        <p data-testid="child">ok</p>
      </ScenePlayerErrorBoundary>,
    );
    expect(screen.getByTestId('child')).toHaveTextContent('ok');
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('renders the fallback with PLAYER_RENDER_ERROR code when a child throws', () => {
    const Exploding = () => {
      throw new Error('render crash');
    };

    expect(() =>
      render(
        <ScenePlayerErrorBoundary>
          <Exploding />
        </ScenePlayerErrorBoundary>,
      ),
    ).not.toThrow();

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent(/Không thể xem trước/);
    expect(alert).toHaveTextContent(/PLAYER_RENDER_ERROR/);
  });
});
