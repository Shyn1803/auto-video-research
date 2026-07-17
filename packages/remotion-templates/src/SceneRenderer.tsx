import {AbsoluteFill, Sequence} from 'remotion';

import {Animated} from './motion/Animated';
import {Subtitle} from './primitives/Subtitle';
import {prepareSubtitleProps, type SubtitleSpecInput, type VoiceSpecInput} from './subtitle/prepareSubtitleProps';

export type SceneProps = {
  duration_ms: number;
  format?: 'vertical_1080x1920' | 'horizontal_1920x1080';
  schema_version: string;
  motion_plan?: {tracks: MotionTrack[]};
  // Mirrors backend/app/schemas/scene.py VoiceSpec/SubtitleSpec (field names
  // kept identical — no generated TS type exists yet, see prepareSubtitleProps.ts).
  voice?: VoiceSpecInput | null;
  subtitle?: SubtitleSpecInput;
};

export type MotionTrack = {
  component_id: string;
  preset: string;
  enter_at_ms: number;
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

export const msToFrames = (milliseconds: number, fps: number): number =>
  Math.round((milliseconds / 1000) * fps);

export const SceneRenderer = (props: SceneProps) => {
  // Subtitle defaults to enabled for any scene with voice (Decisions already
  // locked, task 2-5). SubtitleSpec itself already defaults enabled=true
  // backend-side (scene.py), this local default only covers previews that
  // omit the field entirely.
  const subtitleProps = prepareSubtitleProps(props.voice, props.subtitle ?? {enabled: true, style: 'line'});

  return (
    <AbsoluteFill>
      {props.motion_plan?.tracks.map((track) => (
        <Sequence
          key={track.component_id}
          from={msToFrames(track.enter_at_ms, 30)}
          durationInFrames={Infinity}
          layout="none"
          name={`Motion ${track.component_id}`}
        >
          <Animated preset={track.preset}>
            <span data-component-id={track.component_id} />
          </Animated>
        </Sequence>
      ))}
      <Sequence
        from={0}
        durationInFrames={Infinity}
        layout="none"
        name="Subtitle"
      >
        <Subtitle enabled={subtitleProps.enabled} segments={subtitleProps.segments} />
      </Sequence>
    </AbsoluteFill>
  );
};
