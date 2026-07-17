import {useMemo} from 'react';
import {AbsoluteFill, Sequence} from 'remotion';

import {Animated} from './motion/Animated';
import {Subtitle, type SubtitleSpec} from './primitives/Subtitle';
import {segmentTimestamps, type WordTimestamp} from './subtitle/segmentTimestamps';

export type SceneProps = {
  duration_ms: number;
  format?: 'vertical_1080x1920' | 'horizontal_1920x1080';
  schema_version: string;
  motion_plan?: {tracks: MotionTrack[]};
  /** Per scene-json-schema.md §3.4 VoiceSpec — `audio` is null until the
   * Voice Worker has produced it; subtitle segments only render once it's
   * populated with word timestamps. */
  voice?: {
    audio?: {timestamps: WordTimestamp[]} | null;
  };
  /** Per scene-json-schema.md §3.4 SubtitleSpec — default `{enabled: true,
   * style: "line"}` per "Decisions already locked" (subtitle on by default
   * for any scene with voice). */
  subtitle?: SubtitleSpec;
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

// Default per "Decisions already locked" — subtitle on by default for any
// scene with voice; AI/Layout Engine never has to set this explicitly.
const DEFAULT_SUBTITLE: SubtitleSpec = {enabled: true, style: 'line'};

export const SceneRenderer = (props: SceneProps) => {
  const timestamps = props.voice?.audio?.timestamps ?? [];
  // Segments are derived at render/preview time — never stored in Scene
  // JSON (scene-json-schema.md §3.4) — recomputed only when the underlying
  // timestamps actually change.
  const segments = useMemo(() => segmentTimestamps(timestamps), [timestamps]);

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
      <Subtitle subtitle={props.subtitle ?? DEFAULT_SUBTITLE} segments={segments} />
    </AbsoluteFill>
  );
};
