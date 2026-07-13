'use client';

import type {PlayerRef} from '@remotion/player';
import type {RefObject} from 'react';
import {useCallback, useEffect, useState} from 'react';

export const useScenePlayerProgress = (playerRef: RefObject<PlayerRef | null>) => {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    const player = playerRef.current;
    if (!player) return;
    const onFrame = (event: {detail: {frame: number}}) => setFrame(event.detail.frame);
    player.addEventListener('frameupdate', onFrame);
    return () => player.removeEventListener('frameupdate', onFrame);
  }, [playerRef]);

  const seekTo = useCallback((nextFrame: number) => playerRef.current?.seekTo(nextFrame), [playerRef]);
  return {frame, seekTo};
};
