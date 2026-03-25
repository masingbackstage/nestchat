import { get, writable } from 'svelte/store';
import type { FriendRequest, FriendUser, UserSearchResult } from '../../../types/gateway';
import { DM_CACHE_TTL_MS } from '../messages/utils';
import { loadDMFriendsCache, saveDMFriendsCache } from '../storage';
import {
  deleteFriendRelation,
  fetchFriendsData,
  postAcceptFriendRequest,
  postDeclineFriendRequest,
  postFriendRequest,
  searchUsersRequest,
} from './api';

export const friends = writable<FriendUser[]>([]);
export const incomingFriendRequests = writable<FriendRequest[]>([]);
export const outgoingFriendRequests = writable<FriendRequest[]>([]);
export const friendsLoading = writable(false);
export const friendsRefreshing = writable(false);
export const friendsError = writable<string | null>(null);
export const friendsStorageHydrated = writable(false);
let inFlightLoad: Promise<void> | null = null;
let friendsFetchedAt: number | null = null;
let storageReady = false;

function hasFriendsCache(): boolean {
  return friendsFetchedAt !== null;
}

function isFriendsCacheFresh(): boolean {
  if (!friendsFetchedAt) {
    return false;
  }

  return Date.now() - friendsFetchedAt <= DM_CACHE_TTL_MS;
}

function persistFriendsSnapshot(): void {
  if (!storageReady) {
    return;
  }

  saveDMFriendsCache(
    get(friends),
    get(incomingFriendRequests),
    get(outgoingFriendRequests),
    friendsFetchedAt ??
      (get(friends).length > 0 ||
      get(incomingFriendRequests).length > 0 ||
      get(outgoingFriendRequests).length > 0
        ? Date.now()
        : null),
  );
}

export async function loadFriendsData(force = false): Promise<void> {
  if (inFlightLoad) {
    return inFlightLoad;
  }

  if (!force && hasFriendsCache() && isFriendsCacheFresh()) {
    return;
  }

  const run = (async () => {
    const background = !force && hasFriendsCache();
    if (background) {
      friendsRefreshing.set(true);
    } else {
      friendsLoading.set(true);
    }
    friendsError.set(null);
    try {
      const payload = await fetchFriendsData();
      friendsFetchedAt = Date.now();
      friends.set(payload.friends);
      incomingFriendRequests.set(payload.incomingRequests);
      outgoingFriendRequests.set(payload.outgoingRequests);
    } catch (error) {
      friendsError.set(error instanceof Error ? error.message : 'Failed to load friends data.');
    } finally {
      friendsLoading.set(false);
      friendsRefreshing.set(false);
    }
  })();

  inFlightLoad = run;
  try {
    await run;
  } finally {
    inFlightLoad = null;
  }
}

export async function sendFriendRequest(userUuid: string): Promise<void> {
  await postFriendRequest(userUuid);
  await loadFriendsData();
}

export async function acceptFriendRequest(requestUuid: string): Promise<void> {
  await postAcceptFriendRequest(requestUuid);
  await loadFriendsData();
}

export async function declineFriendRequest(requestUuid: string): Promise<void> {
  await postDeclineFriendRequest(requestUuid);
  await loadFriendsData();
}

export async function removeFriendRelation(relationUuid: string): Promise<void> {
  await deleteFriendRelation(relationUuid);
  await loadFriendsData();
}

export async function searchUsers(query: string): Promise<UserSearchResult[]> {
  const normalized = query.trim();
  if (normalized.length < 2) {
    return [];
  }

  return searchUsersRequest(normalized);
}

export function resetFriendsState(): void {
  friends.set([]);
  incomingFriendRequests.set([]);
  outgoingFriendRequests.set([]);
  friendsLoading.set(false);
  friendsRefreshing.set(false);
  friendsStorageHydrated.set(false);
  friendsError.set(null);
  inFlightLoad = null;
  friendsFetchedAt = null;
  storageReady = false;
}

export function hydrateFriendsStateFromStorage(): void {
  if (storageReady) {
    return;
  }

  const cache = loadDMFriendsCache();
  friendsFetchedAt = cache.savedAt;
  friends.set(cache.friends);
  incomingFriendRequests.set(cache.incomingRequests);
  outgoingFriendRequests.set(cache.outgoingRequests);
  storageReady = true;
  friendsStorageHydrated.set(true);
}

friends.subscribe(() => {
  persistFriendsSnapshot();
});

incomingFriendRequests.subscribe(() => {
  persistFriendsSnapshot();
});

outgoingFriendRequests.subscribe(() => {
  persistFriendsSnapshot();
});
