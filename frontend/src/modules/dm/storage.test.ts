import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { DMConversation, DMMessage, FriendRequest, FriendUser } from '../../types/gateway';
import type { DMQueryState } from './messages/types';

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

describe('dm storage helpers', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
  });

  it('round-trips DM and friends caches', async () => {
    mockLocalStorage();
    const storage = await import('./storage');

    const conversations: DMConversation[] = [
      { uuid: 'conv-1', updated_at: '2026-01-01T00:00:00.000Z' },
    ];
    const messagesByConversation: Record<string, DMMessage[]> = {
      'conv-1': [
        {
          uuid: 'msg-1',
          conversation_uuid: 'conv-1',
          channel_uuid: 'conv-1',
          content: 'hello',
          author: 'A',
        },
      ],
    };
    const queryStateByConversation: Record<string, DMQueryState> = {
      'conv-1': {
        fetchedAt: 123,
        isLoadingInitial: false,
        isLoadingOlder: false,
        isLoadingNewer: false,
        hasMoreOlder: false,
        hasMoreNewer: false,
        nextBefore: null,
        nextAfter: null,
        error: null,
      },
    };
    const friends: FriendUser[] = [{ uuid: 'user-1', email: 'a@example.com' }];
    const incomingRequests: FriendRequest[] = [];
    const outgoingRequests: FriendRequest[] = [];

    storage.saveDMConversationsCache(conversations, 999);
    storage.saveDMMessagesCache(messagesByConversation, queryStateByConversation);
    storage.saveDMFriendsCache(friends, incomingRequests, outgoingRequests, 555);
    storage.saveDMUICache({
      activeConversationUuid: 'conv-1',
      activeServerUuid: 'server-1',
      activeChannelUuid: 'channel-1',
      isDMView: false,
    });

    expect(storage.loadDMConversationsCache()).toEqual({
      conversations,
      savedAt: 999,
    });
    expect(storage.loadDMMessagesCache()).toEqual({
      messagesByConversation,
      queryStateByConversation,
    });
    expect(storage.loadDMFriendsCache()).toEqual({
      friends,
      incomingRequests,
      outgoingRequests,
      savedAt: 555,
    });
    expect(storage.loadDMUICache()).toEqual({
      activeConversationUuid: 'conv-1',
      activeServerUuid: 'server-1',
      activeChannelUuid: 'channel-1',
      isDMView: false,
    });
  });

  it('falls back safely on invalid JSON', async () => {
    mockLocalStorage({
      dm_conversations_cache_v1: '{broken',
      dm_messages_cache_v1: '{broken',
      dm_friends_cache_v1: '{broken',
      dm_ui_cache_v1: '{broken',
    });
    const storage = await import('./storage');

    expect(storage.loadDMConversationsCache()).toEqual({
      conversations: [],
      savedAt: null,
    });
    expect(storage.loadDMMessagesCache()).toEqual({
      messagesByConversation: {},
      queryStateByConversation: {},
    });
    expect(storage.loadDMFriendsCache()).toEqual({
      friends: [],
      incomingRequests: [],
      outgoingRequests: [],
      savedAt: null,
    });
    expect(storage.loadDMUICache()).toEqual({
      activeConversationUuid: null,
      activeServerUuid: null,
      activeChannelUuid: null,
      isDMView: false,
    });
  });
});
