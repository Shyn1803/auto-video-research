import {readFileSync, readdirSync} from 'node:fs';
import {join} from 'node:path';
import {describe, expect, it} from 'vitest';

import {sceneSchema} from '../schema';

const fixtures = join(process.cwd(), 'schema', 'fixtures');
const load = (name: string): unknown => JSON.parse(readFileSync(join(fixtures, name), 'utf8'));

describe('shared Scene JSON fixtures', () => {
  it('accepts every valid fixture', () => {
    for (const name of readdirSync(fixtures).filter((entry) => entry.endsWith('.valid.json'))) {
      expect(sceneSchema.safeParse(load(name)).success, name).toBe(true);
    }
  });

  it('rejects wrong duration and missing required fields', () => {
    expect(sceneSchema.safeParse(load('duration-type.invalid.json')).success).toBe(false);
    expect(sceneSchema.safeParse(load('missing-scene-id.invalid.json')).success).toBe(false);
  });
});
