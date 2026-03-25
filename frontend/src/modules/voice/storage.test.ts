import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DEFAULT_VOICE_THRESHOLD } from './gate';

function mockLocalStorage(seed: Record<string, string> = {}) {
  const state = new Map(Object.entries(seed));

  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: vi.fn((key: string) => state.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => {
        state.set(key, value);
      }),
      removeItem: vi.fn((key: string) => {
        state.delete(key);
      }),
      clear: vi.fn(() => {
        state.clear();
      }),
    },
  });

  return state;
}

describe('voice storage helpers', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
  });

  it('loads the default threshold when storage is empty', async () => {
    mockLocalStorage();
    const storage = await import('./storage');

    expect(storage.loadVoiceThreshold()).toBe(DEFAULT_VOICE_THRESHOLD);
  });

  it('round-trips a stored threshold', async () => {
    mockLocalStorage();
    const storage = await import('./storage');

    storage.saveVoiceThreshold(0.04);

    expect(storage.loadVoiceThreshold()).toBe(0.04);
  });

  it('falls back safely on invalid JSON', async () => {
    mockLocalStorage({
      voice_settings_v1: '{broken',
    });
    const storage = await import('./storage');

    expect(storage.loadVoiceThreshold()).toBe(DEFAULT_VOICE_THRESHOLD);
  });
});
