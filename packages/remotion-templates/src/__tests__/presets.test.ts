import {readdirSync, readFileSync} from 'node:fs';
import {join} from 'node:path';
import {describe, expect, it} from 'vitest';

const directory = join(process.cwd(), 'src', 'presets', 'layouts');

describe('base layout preset matrix', () => {
  it('contains five layouts for both supported formats', () => {
    const files = readdirSync(directory).filter((file) => file.endsWith('.json'));
    expect(files).toHaveLength(10);
    for (const file of files) {
      const preset = JSON.parse(readFileSync(join(directory, file), 'utf8')) as Record<string, unknown>;
      expect(preset).toMatchObject({layout: expect.any(String), format: expect.any(String), direction: expect.any(String)});
      expect(['vertical_1080x1920', 'horizontal_1920x1080']).toContain(preset.format);
    }
  });

  it('uses a responsive MediaText direction', () => {
    const vertical = JSON.parse(readFileSync(join(directory, 'media-text.9x16.json'), 'utf8')) as {direction: string};
    const horizontal = JSON.parse(readFileSync(join(directory, 'media-text.16x9.json'), 'utf8')) as {direction: string};
    expect(vertical.direction).toBe('column');
    expect(horizontal.direction).toBe('row');
  });
});
