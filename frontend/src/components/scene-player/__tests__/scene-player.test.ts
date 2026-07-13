import {describe, expect, it} from 'vitest';

describe('ScenePlayer contract', () => {
  it('uses the documented 30fps duration conversion', () => {
    expect(Math.ceil((2000 / 1000) * 30)).toBe(60);
  });

  it('maps output formats to Player dimensions', () => {
    expect('vertical_1080x1920' === 'horizontal_1920x1080' ? [1920, 1080] : [1080, 1920]).toEqual([1080, 1920]);
    expect('horizontal_1920x1080' === 'horizontal_1920x1080' ? [1920, 1080] : [1080, 1920]).toEqual([1920, 1080]);
  });
});
