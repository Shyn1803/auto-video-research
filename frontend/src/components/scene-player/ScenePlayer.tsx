'use client';

import {Player, type PlayerRef} from '@remotion/player';
import {useMemo, useRef} from 'react';
import type {ComponentType} from 'react';

type SceneInput = {duration_ms: number; format?: 'vertical_1080x1920' | 'horizontal_1920x1080'; voice?: {audio?: unknown} | null};

export const ScenePlayer = ({component, scene}: {component: ComponentType<SceneInput>; scene: SceneInput}) => {
  const ref = useRef<PlayerRef>(null);
  const dimensions = scene.format === 'horizontal_1920x1080' ? [1920, 1080] : [1080, 1920];
  const key = useMemo(() => JSON.stringify(scene), [scene]);
  const hasAudio = Boolean(scene.voice?.audio);

  return (
    <div>
      {!hasAudio && <p role="status">Chưa tạo giọng đọc</p>}
      <Player key={key} ref={ref} component={component} inputProps={scene} durationInFrames={Math.ceil(scene.duration_ms / 1000 * 30)} fps={30} compositionWidth={dimensions[0]} compositionHeight={dimensions[1]} controls />
    </div>
  );
};
