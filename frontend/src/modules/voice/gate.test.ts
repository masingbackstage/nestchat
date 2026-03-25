import { describe, expect, it } from 'vitest';
import {
  DEFAULT_VOICE_HANGOVER_MS,
  DEFAULT_VOICE_THRESHOLD,
  MAX_VOICE_THRESHOLD,
  MIN_VOICE_THRESHOLD,
  clampVoiceThreshold,
  nextVoiceGateState,
} from './gate';

describe('voice gate helpers', () => {
  it('clamps threshold to a safe supported range', () => {
    expect(clampVoiceThreshold(Number.NaN)).toBe(DEFAULT_VOICE_THRESHOLD);
    expect(clampVoiceThreshold(0)).toBe(MIN_VOICE_THRESHOLD);
    expect(clampVoiceThreshold(999)).toBe(MAX_VOICE_THRESHOLD);
    expect(clampVoiceThreshold(0.03)).toBe(0.03);
  });

  it('keeps gate open during short pauses and closes after hangover', () => {
    const initial = { isOpen: false, lastVoiceAtMs: null };

    const opened = nextVoiceGateState(initial, {
      level: 0.05,
      threshold: DEFAULT_VOICE_THRESHOLD,
      nowMs: 1_000,
      hangoverMs: DEFAULT_VOICE_HANGOVER_MS,
    });
    expect(opened).toEqual({ isOpen: true, lastVoiceAtMs: 1_000 });

    const shortPause = nextVoiceGateState(opened, {
      level: 0.005,
      threshold: DEFAULT_VOICE_THRESHOLD,
      nowMs: 1_200,
      hangoverMs: DEFAULT_VOICE_HANGOVER_MS,
    });
    expect(shortPause).toEqual(opened);

    const closed = nextVoiceGateState(shortPause, {
      level: 0.005,
      threshold: DEFAULT_VOICE_THRESHOLD,
      nowMs: 1_350,
      hangoverMs: DEFAULT_VOICE_HANGOVER_MS,
    });
    expect(closed).toEqual({ isOpen: false, lastVoiceAtMs: 1_000 });
  });
});
