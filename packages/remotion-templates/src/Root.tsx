import {Composition} from 'remotion';

import {SceneRenderer} from './SceneRenderer';
import {sceneSchema} from './schema';

export const RemotionRoot = () => (
  <Composition
    id="Scene"
    component={SceneRenderer}
    defaultProps={{}}
    durationInFrames={1}
    fps={30}
    width={1080}
    height={1920}
    schema={sceneSchema}
  />
);
