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
}

async function loadStore() {
  vi.resetModules();
  vi.stubEnv('VITE_API_URL', 'http://api.test');
  return await import('./store');
}

describe('dm friends store hydration', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it('hydrates cached friends and refreshes stale cache in background', async () => {
    mockLocalStorage({
      dm_friends_cache_v1: JSON.stringify({
        friends: [{ uuid: 'user-1', email: 'friend@example.com' }],
        incomingRequests: [],
        outgoingRequests: [],
        savedAt: Date.now() - 120_000,
      }),
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const rawUrl = typeof input === 'string' ? input : input.toString();
      if (rawUrl.includes('/friends/requests/incoming/')) {
        return { ok: true, status: 200, json: async () => [] } as Response;
      }
      if (rawUrl.includes('/friends/requests/outgoing/')) {
        return { ok: true, status: 200, json: async () => [] } as Response;
      }
      return {
        ok: true,
        status: 200,
        json: async () => [{ uuid: 'rel-1', user: { uuid: 'user-2', email: 'fresh@example.com' } }],
      } as Response;
    });
    vi.stubGlobal('fetch', fetchMock);

    const store = await loadStore();
    store.hydrateFriendsStateFromStorage();

    const refreshPromise = store.loadFriendsData();
    expect(get(store.friendsLoading)).toBe(false);
    expect(get(store.friendsRefreshing)).toBe(true);
    expect(get(store.friends)[0]?.uuid).toBe('user-1');

    await refreshPromise;

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(get(store.friendsRefreshing)).toBe(false);
    expect(get(store.friends)[0]?.uuid).toBe('user-2');
  });
});
