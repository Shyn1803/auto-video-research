import {readdirSync, readFileSync} from 'node:fs';
import {join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const directory = join(__dirname, '..', 'presets', 'layouts');

// Map PascalCase layout class → filename prefix (kebab-case with special cases)
const LAYOUT_FILENAME: Record<string, string> = {
  Hero: 'hero',
  TextFocus: 'text-focus',
  MediaFull: 'media-full',
  MediaText: 'media-text',
  Comparison: 'comparison',
  BigNumber: 'big-number',
  Chart: 'chart',
  VersusTable: 'versus-table',
  List: 'list',
  Quote: 'quote',
  Code: 'code',
};

const LAYOUT_CLASSES: string[] = Object.keys(LAYOUT_FILENAME);

const layoutFile = (layout: string, suffix: '9x16' | '16x9') =>
  `${LAYOUT_FILENAME[layout]}.${suffix}.json`;

describe('layout preset matrix', () => {
  it('contains 11 layouts for both supported formats (22 files total)', () => {
    const files = readdirSync(directory).filter((file) => file.endsWith('.json'));
    expect(files).toHaveLength(22);
    for (const file of files) {
      const preset = JSON.parse(readFileSync(join(directory, file), 'utf8')) as Record<string, unknown>;
      expect(preset).toMatchObject({layout: expect.any(String), format: expect.any(String), direction: expect.any(String)});
      expect(['vertical_1080x1920', 'horizontal_1920x1080']).toContain(preset.format);
      expect(LAYOUT_CLASSES).toContain((preset.layout as string));
    }
  });

  it('has a preset for every layout class in both formats', () => {
    for (const layout of LAYOUT_CLASSES) {
      expect(
        readdirSync(directory).filter((f) => f.startsWith(LAYOUT_FILENAME[layout]) && f.endsWith('.json')),
      ).toHaveLength(2);
    }
  });

  it('uses a responsive MediaText direction (column vertical, row horizontal)', () => {
    const vertical = JSON.parse(readFileSync(join(directory, 'media-text.9x16.json'), 'utf8')) as {direction: string};
    const horizontal = JSON.parse(readFileSync(join(directory, 'media-text.16x9.json'), 'utf8')) as {direction: string};
    expect(vertical.direction).toBe('column');
    expect(horizontal.direction).toBe('row');
  });

  it.each(LAYOUT_CLASSES)('has valid JSON for %s 9:16 preset', (layout) => {
    const preset = JSON.parse(readFileSync(join(directory, layoutFile(layout, '9x16')), 'utf8'));
    expect(preset.layout).toBe(layout);
    expect(preset.format).toBe('vertical_1080x1920');
  });

  it.each(LAYOUT_CLASSES)('has valid JSON for %s 16:9 preset', (layout) => {
    const preset = JSON.parse(readFileSync(join(directory, layoutFile(layout, '16x9')), 'utf8'));
    expect(preset.layout).toBe(layout);
    expect(preset.format).toBe('horizontal_1920x1080');
  });
});
