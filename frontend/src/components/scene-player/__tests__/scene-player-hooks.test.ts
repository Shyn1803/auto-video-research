import {describe, expect, it, vi} from 'vitest';
import {renderHook, act} from '@testing-library/react';
import {useScenePlayerProgress} from '../useScenePlayerProgress';
import {useScenePlayerThumbnail} from '../useScenePlayerThumbnail';

const makeFakePlayer = () => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  seekTo: vi.fn(),
});

describe('useScenePlayerProgress', () => {
  it('returns initial frame 0', () => {
    const ref = {current: makeFakePlayer()};
    const {result} = renderHook(() => useScenePlayerProgress(ref));
    expect(result.current.frame).toBe(0);
  });

  it('exposes a seekTo function', () => {
    const ref = {current: makeFakePlayer()};
    const {result} = renderHook(() => useScenePlayerProgress(ref));
    expect(typeof result.current.seekTo).toBe('function');
  });

  it('subscribes to the frameupdate event on mount', () => {
    const player = makeFakePlayer();
    const ref = {current: player};
    renderHook(() => useScenePlayerProgress(ref));
    expect(player.addEventListener).toHaveBeenCalledWith(
      'frameupdate',
      expect.any(Function),
    );
  });

  it('removes the listener on unmount', () => {
    const player = makeFakePlayer();
    const ref = {current: player};
    const {unmount} = renderHook(() => useScenePlayerProgress(ref));
    unmount();
    expect(player.removeEventListener).toHaveBeenCalledWith(
      'frameupdate',
      expect.any(Function),
    );
  });

  it('updates frame when the player emits a frameupdate event', () => {
    const capturedHandlers: ((ev: {detail: {frame: number}}) => void)[] = [];
    const player = {
      addEventListener: (_event: string, handler: (ev: {detail: {frame: number}}) => void) => {
        capturedHandlers.push(handler);
      },
      removeEventListener: vi.fn(),
      seekTo: vi.fn(),
    };
    const ref = {current: player};
    const {result} = renderHook(() => useScenePlayerProgress(ref));

    act(() => {
      capturedHandlers[0]({detail: {frame: 42}});
    });

    expect(result.current.frame).toBe(42);
  });
});

describe('useScenePlayerThumbnail', () => {
  it('calls seekTo on the player with the requested frame', () => {
    const player = makeFakePlayer();
    const ref = {current: player};
    const {result} = renderHook(() => useScenePlayerThumbnail(ref));

    act(() => {
      result.current(15);
    });

    expect(player.seekTo).toHaveBeenCalledWith(15);
  });

  it('returns the frame without throwing when the player ref is null', () => {
    const ref = {current: null};
    const {result} = renderHook(() => useScenePlayerThumbnail(ref));
    expect(() => result.current(10)).not.toThrow();
    expect(result.current(10)).toBe(10);
  });
});
