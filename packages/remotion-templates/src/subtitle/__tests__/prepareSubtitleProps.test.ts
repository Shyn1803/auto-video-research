import {describe, expect, it} from 'vitest';
import {prepareSubtitleProps} from '../prepareSubtitleProps';

// Fixture shaped like 2-4's TTS adapter output (VoiceSpec.audio.timestamps).
const voiceWithAudio = {
  audio: {
    timestamps: [
      {word: 'Xin', start_ms: 0, end_ms: 200},
      {word: 'chào', start_ms: 200, end_ms: 400},
      {word: 'các', start_ms: 400, end_ms: 600},
      {word: 'bạn', start_ms: 600, end_ms: 900},
    ],
  },
};

describe('prepareSubtitleProps', () => {
  it('produces segments from voice audio timestamps when subtitle is enabled (line style)', () => {
    const result = prepareSubtitleProps(voiceWithAudio, {enabled: true, style: 'line'});
    expect(result.enabled).toBe(true);
    expect(result.segments.length).toBeGreaterThan(0);
    expect(result.segments.map((s) => s.text).join(' ')).toBe('Xin chào các bạn');
  });

  it('is disabled when subtitle.enabled=false (BR-3), regardless of available timestamps', () => {
    const result = prepareSubtitleProps(voiceWithAudio, {enabled: false, style: 'line'});
    expect(result).toEqual({enabled: false, segments: []});
  });

  it('is disabled when the scene has no voice/audio (nothing to segment)', () => {
    expect(prepareSubtitleProps(null, {enabled: true, style: 'line'})).toEqual({enabled: false, segments: []});
    expect(prepareSubtitleProps({audio: null}, {enabled: true, style: 'line'})).toEqual({
      enabled: false,
      segments: [],
    });
  });

  it('is disabled for karaoke style (out of scope for 2-5, v2)', () => {
    expect(prepareSubtitleProps(voiceWithAudio, {enabled: true, style: 'karaoke'})).toEqual({
      enabled: false,
      segments: [],
    });
  });
});
