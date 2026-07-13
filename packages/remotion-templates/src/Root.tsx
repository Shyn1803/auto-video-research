import {Composition} from 'remotion';

import {SceneRenderer, sceneMetadata, type SceneProps} from './SceneRenderer';
import {sceneSchema} from './schema';
import {VideoRenderer, type VideoProps} from './VideoRenderer';

export const RemotionRoot = () => (
  <>
    <Composition id="Scene" component={SceneRenderer} defaultProps={{duration_ms: 1000, schema_version: '1.0.0'} satisfies SceneProps} durationInFrames={1} fps={30} width={1080} height={1920} schema={sceneSchema} calculateMetadata={sceneMetadata} />
    <Composition id="Video" component={VideoRenderer} defaultProps={{scenes: []} satisfies VideoProps} durationInFrames={1} fps={30} width={1080} height={1920} />
  </>
);
