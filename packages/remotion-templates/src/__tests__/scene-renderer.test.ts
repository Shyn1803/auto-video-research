import {describe, expect, it} from 'vitest';

import {assertSupportedSchema, msToFrames, sceneMetadata} from '../SceneRenderer';

describe('SceneRenderer metadata', () => {
  it('converts milliseconds to frames at the composition fps', () => {
    expect(msToFrames(500, 30)).toBe(15);
    expect(msToFrames(1000, 30)).toBe(30);
  });

  it('resolves format-specific metadata', () => {
    expect(sceneMetadata({props: {duration_ms: 2000, schema_version: '1.0.0'}})).toMatchObject({
      width: 1080,
      height: 1920,
      durationInFrames: 60,
    });
    expect(
      sceneMetadata({
        props: {duration_ms: 2000, schema_version: '1.0.0', format: 'horizontal_1920x1080'},
      }),
    ).toMatchObject({width: 1920, height: 1080});
  });

  it('throws SCHEMA_RANGE for unsupported schema versions', () => {
    expect(() => assertSupportedSchema('2.0.0')).toThrow(/SCHEMA_RANGE|outside/);
  });
});
