'use client';

import type {PlayerRef} from '@remotion/player';
import type {RefObject} from 'react';
import {useCallback} from 'react';

export const useScenePlayerThumbnail = (playerRef: RefObject<PlayerRef | null>) =>
  useCallback((frame: number) => {
    playerRef.current?.seekTo(frame);
    return frame;
  }, [playerRef]);
