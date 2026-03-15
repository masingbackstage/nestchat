import { writable } from 'svelte/store';
import type { FriendRequest, FriendUser, UserSearchResult } from '../../../types/gateway';
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
export const friendsError = writable<string | null>(null);
let inFlightLoad: Promise<void> | null = null;

export async function loadFriendsData(): Promise<void> {
  if (inFlightLoad) {
    return inFlightLoad;
  }

  const run = (async () => {
    friendsLoading.set(true);
    friendsError.set(null);
    try {
      const payload = await fetchFriendsData();
      friends.set(payload.friends);
      incomingFriendRequests.set(payload.incomingRequests);
      outgoingFriendRequests.set(payload.outgoingRequests);
    } catch (error) {
      friendsError.set(error instanceof Error ? error.message : 'Failed to load friends data.');
    } finally {
      friendsLoading.set(false);
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
  friendsError.set(null);
  inFlightLoad = null;
}
