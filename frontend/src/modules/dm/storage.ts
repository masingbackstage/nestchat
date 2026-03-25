import type { DMConversation, DMMessage, FriendRequest, FriendUser } from '../../types/gateway';
import type { DMQueryState } from './messages/types';

const DM_CONVERSATIONS_STORAGE_KEY = 'dm_conversations_cache_v1';
const DM_MESSAGES_STORAGE_KEY = 'dm_messages_cache_v1';
const DM_FRIENDS_STORAGE_KEY = 'dm_friends_cache_v1';
const DM_UI_STORAGE_KEY = 'dm_ui_cache_v1';
const MAX_PERSISTED_MESSAGES_PER_CONVERSATION = 300;

type StoredDMConversations = {
  conversations: DMConversation[];
  savedAt: number | null;
};

type StoredDMMessages = {
  messagesByConversation: Record<string, DMMessage[]>;
  queryStateByConversation: Record<string, DMQueryState>;
};

type StoredDMFriends = {
  friends: FriendUser[];
  incomingRequests: FriendRequest[];
  outgoingRequests: FriendRequest[];
  savedAt: number | null;
};

export type StoredDMUI = {
  activeConversationUuid: string | null;
  activeServerUuid: string | null;
  activeChannelUuid: string | null;
  isDMView: boolean;
};

function hasLocalStorage(): boolean {
  return typeof localStorage !== 'undefined';
}

function loadJson<T>(key: string, fallback: T): T {
  if (!hasLocalStorage()) {
    return fallback;
  }

  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }

    return (JSON.parse(raw) as T) ?? fallback;
  } catch {
    return fallback;
  }
}

function saveJson<T>(key: string, value: T): void {
  if (!hasLocalStorage()) {
    return;
  }

  localStorage.setItem(key, JSON.stringify(value));
}

function trimMessagesCache(
  messagesByConversation: Record<string, DMMessage[]>,
): Record<string, DMMessage[]> {
  return Object.fromEntries(
    Object.entries(messagesByConversation).map(([conversationUuid, messages]) => [
      conversationUuid,
      messages.slice(-MAX_PERSISTED_MESSAGES_PER_CONVERSATION),
    ]),
  );
}

export function loadDMConversationsCache(): StoredDMConversations {
  return loadJson<StoredDMConversations>(DM_CONVERSATIONS_STORAGE_KEY, {
    conversations: [],
    savedAt: null,
  });
}

export function saveDMConversationsCache(
  conversations: DMConversation[],
  savedAt: number | null,
): void {
  saveJson<StoredDMConversations>(DM_CONVERSATIONS_STORAGE_KEY, {
    conversations,
    savedAt,
  });
}

export function loadDMMessagesCache(): StoredDMMessages {
  return loadJson<StoredDMMessages>(DM_MESSAGES_STORAGE_KEY, {
    messagesByConversation: {},
    queryStateByConversation: {},
  });
}

export function saveDMMessagesCache(
  messagesByConversation: Record<string, DMMessage[]>,
  queryStateByConversation: Record<string, DMQueryState>,
): void {
  saveJson<StoredDMMessages>(DM_MESSAGES_STORAGE_KEY, {
    messagesByConversation: trimMessagesCache(messagesByConversation),
    queryStateByConversation,
  });
}

export function loadDMFriendsCache(): StoredDMFriends {
  return loadJson<StoredDMFriends>(DM_FRIENDS_STORAGE_KEY, {
    friends: [],
    incomingRequests: [],
    outgoingRequests: [],
    savedAt: null,
  });
}

export function saveDMFriendsCache(
  friends: FriendUser[],
  incomingRequests: FriendRequest[],
  outgoingRequests: FriendRequest[],
  savedAt: number | null,
): void {
  saveJson<StoredDMFriends>(DM_FRIENDS_STORAGE_KEY, {
    friends,
    incomingRequests,
    outgoingRequests,
    savedAt,
  });
}

export function loadDMUICache(): StoredDMUI {
  const cache = loadJson<Partial<StoredDMUI>>(DM_UI_STORAGE_KEY, {});
  return {
    activeConversationUuid: cache.activeConversationUuid ?? null,
    activeServerUuid: cache.activeServerUuid ?? null,
    activeChannelUuid: cache.activeChannelUuid ?? null,
    isDMView: cache.isDMView ?? false,
  };
}

export function saveDMUICache(cache: StoredDMUI): void {
  saveJson<StoredDMUI>(DM_UI_STORAGE_KEY, {
    activeConversationUuid: cache.activeConversationUuid,
    activeServerUuid: cache.activeServerUuid,
    activeChannelUuid: cache.activeChannelUuid,
    isDMView: cache.isDMView,
  });
}

export function clearDMStorage(): void {
  if (!hasLocalStorage()) {
    return;
  }

  localStorage.removeItem(DM_CONVERSATIONS_STORAGE_KEY);
  localStorage.removeItem(DM_MESSAGES_STORAGE_KEY);
  localStorage.removeItem(DM_FRIENDS_STORAGE_KEY);
  localStorage.removeItem(DM_UI_STORAGE_KEY);
}
