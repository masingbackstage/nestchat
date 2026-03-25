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

async function loadStore() {
  vi.resetModules();
  vi.stubEnv('VITE_API_URL', 'http://api.test');
  const ui = await import('../../../lib/stores/ui');
  const store = await import('./store');
  return { ui, store };
}

describe('dm messages store hydration', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it('hydrates conversations and active DM from localStorage', async () => {
    mockLocalStorage({
      dm_conversations_cache_v1: JSON.stringify({
        conversations: [
          {
            uuid: 'conv-1',
            participants: [{ uuid: 'user-2', display_name: 'User 2' }],
            updated_at: '2026-01-01T00:00:00.000Z',
          },
        ],
        savedAt: Date.now(),
      }),
      dm_messages_cache_v1: JSON.stringify({
        messagesByConversation: {
          'conv-1': [
            {
              uuid: 'msg-1',
              conversation_uuid: 'conv-1',
              channel_uuid: 'conv-1',
              content: 'hello',
              author: 'User 2',
            },
          ],
        },
        queryStateByConversation: {
          'conv-1': {
            fetchedAt: Date.now(),
            isLoadingInitial: false,
            isLoadingOlder: false,
            isLoadingNewer: false,
            hasMoreOlder: false,
            hasMoreNewer: false,
            nextBefore: null,
            nextAfter: null,
            error: null,
          },
        },
      }),
      dm_ui_cache_v1: JSON.stringify({
        activeConversationUuid: 'conv-1',
      }),
    });

    const { ui, store } = await loadStore();
    store.hydrateDMStateFromStorage();

    expect(get(store.dmStorageHydrated)).toBe(true);
    expect(get(store.dmConversations)).toHaveLength(1);
    expect(get(store.dmMessagesByConversation)['conv-1']).toHaveLength(1);
    expect(get(ui.activeDMConversation)?.uuid).toBe('conv-1');
  });

  it('keeps cached conversations visible while stale cache refreshes in background', async () => {
    mockLocalStorage({
      dm_conversations_cache_v1: JSON.stringify({
        conversations: [{ uuid: 'conv-1', updated_at: '2026-01-01T00:00:00.000Z' }],
        savedAt: Date.now() - 120_000,
      }),
      dm_messages_cache_v1: JSON.stringify({
        messagesByConversation: {},
        queryStateByConversation: {},
      }),
      dm_ui_cache_v1: JSON.stringify({
        activeConversationUuid: null,
      }),
    });

    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => [{ uuid: 'conv-2', updated_at: '2026-01-02T00:00:00.000Z' }],
    }));
    vi.stubGlobal('fetch', fetchMock);

    const { store } = await loadStore();
    store.hydrateDMStateFromStorage();

    const refreshPromise = store.ensureDMConversations();
    expect(get(store.dmConversationsLoading)).toBe(false);
    expect(get(store.dmConversationsRefreshing)).toBe(true);
    expect(get(store.dmConversations)[0]?.uuid).toBe('conv-1');

    await refreshPromise;

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(get(store.dmConversationsRefreshing)).toBe(false);
    expect(get(store.dmConversations)[0]?.uuid).toBe('conv-2');
  });
});
