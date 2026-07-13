import {AbsoluteFill} from 'remotion';

export type SceneProps = {
  duration_ms: number;
  format?: 'vertical_1080x1920' | 'horizontal_1920x1080';
  schema_version: string;
};

export const SUPPORTED_SCHEMA_RANGE = '^1.0.0';

export class SchemaRangeError extends Error {
  public readonly code = 'SCHEMA_RANGE';

  public constructor(version: string) {
    super(`Scene schema ${version} is outside ${SUPPORTED_SCHEMA_RANGE}`);
  }
}

export const assertSupportedSchema = (version: string): void => {
  if (!/^1\.\d+\.\d+$/.test(version)) {
    throw new SchemaRangeError(version);
  }
};

export const sceneMetadata = ({props}: {props: SceneProps}) => {
  assertSupportedSchema(props.schema_version);
  const vertical = props.format !== 'horizontal_1920x1080';
  return {
    durationInFrames: Math.ceil((props.duration_ms / 1000) * 30),
    fps: 30,
    width: vertical ? 1080 : 1920,
    height: vertical ? 1920 : 1080,
  };
};

export const SceneRenderer = (_props: SceneProps) => <AbsoluteFill />;
