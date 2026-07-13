import {AbsoluteFill, Sequence} from 'remotion';

import {SceneRenderer, type SceneProps, msToFrames} from './SceneRenderer';

export type VideoProps = {fps?: number; scenes: SceneProps[]};

export const VideoRenderer = ({scenes, fps = 30}: VideoProps) => (
  <AbsoluteFill>
    {scenes.map((scene, index) => (
      <Sequence
        key={`${scene.schema_version}-${index}`}
        from={scenes.slice(0, index).reduce((total, item) => total + msToFrames(item.duration_ms, fps), 0)}
        durationInFrames={msToFrames(scene.duration_ms, fps)}
      >
        <SceneRenderer {...scene} />
      </Sequence>
    ))}
  </AbsoluteFill>
);
