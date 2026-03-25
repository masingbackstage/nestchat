import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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

describe('voice store', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
  });

  it('updates threshold from the public setter and persists it', async () => {
    mockLocalStorage();
    const store = await import('./store');

    store.setVoiceThreshold(0.04);

    expect(get(store.voiceState).threshold).toBe(0.04);
    expect(globalThis.localStorage.setItem).toHaveBeenCalledWith(
      'voice_settings_v1',
      JSON.stringify({ threshold: 0.04 }),
    );
  });

  it('allows cleanup when no local audio session exists', async () => {
    mockLocalStorage();
    const store = await import('./store');

    await expect(store.leaveVoiceCall()).resolves.toBeUndefined();
    expect(get(store.voiceState).status).toBe('idle');
  });
});
