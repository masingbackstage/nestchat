import { writable } from 'svelte/store';
import { authFetch } from '../../lib/auth';
import { toApiAbsoluteUrl } from '../../lib/url';
import type { FriendRequest, FriendUser, UserSearchResult } from '../../types/gateway';

export const friends = writable<FriendUser[]>([]);
export const incomingFriendRequests = writable<FriendRequest[]>([]);
export const outgoingFriendRequests = writable<FriendRequest[]>([]);
export const friendsLoading = writable(false);
export const friendsError = writable<string | null>(null);
let inFlightLoad: Promise<void> | null = null;

function getBaseUrl(): string {
  const base = import.meta.env.VITE_API_URL;
  if (!base) {
    throw new Error('Missing VITE_API_URL.');
  }
  return base;
}

function mapUser(user: FriendUser): FriendUser {
  return {
    ...user,
    avatar_url: toApiAbsoluteUrl(user.avatarUrl ?? user.avatar_url ?? null),
  };
}

function mapRequest(item: FriendRequest): FriendRequest {
  return {
    ...item,
    user: mapUser(item.user),
  };
}

export async function loadFriendsData(): Promise<void> {
  if (inFlightLoad) {
    return inFlightLoad;
  }

  const run = (async () => {
    friendsLoading.set(true);
    friendsError.set(null);
    try {
      const [friendsRes, incomingRes, outgoingRes] = await Promise.all([
        authFetch(`${getBaseUrl()}/friends/`),
        authFetch(`${getBaseUrl()}/friends/requests/incoming/`),
        authFetch(`${getBaseUrl()}/friends/requests/outgoing/`),
      ]);

      if (!friendsRes.ok || !incomingRes.ok || !outgoingRes.ok) {
        throw new Error('Failed to load friends data.');
      }

      const friendsPayload = (await friendsRes.json()) as Array<{ uuid: string; user: FriendUser }>;
      const incomingPayload = (await incomingRes.json()) as FriendRequest[];
      const outgoingPayload = (await outgoingRes.json()) as FriendRequest[];

      const mappedFriends = friendsPayload
        .map((item) => ({
          ...mapUser(item.user),
          relation_uuid: item.uuid,
        }))
        .sort((a, b) => {
          const aOnline = Boolean(a.isOnline ?? a.is_online);
          const bOnline = Boolean(b.isOnline ?? b.is_online);
          if (aOnline !== bOnline) {
            return aOnline ? -1 : 1;
          }
          const aName = (a.displayName ?? a.display_name ?? a.email).toLowerCase();
          const bName = (b.displayName ?? b.display_name ?? b.email).toLowerCase();
          return aName.localeCompare(bName);
        });

      friends.set(mappedFriends);
      incomingFriendRequests.set(incomingPayload.map(mapRequest));
      outgoingFriendRequests.set(outgoingPayload.map(mapRequest));
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
  const response = await authFetch(`${getBaseUrl()}/friends/requests/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_uuid: userUuid }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  await loadFriendsData();
}

export async function acceptFriendRequest(requestUuid: string): Promise<void> {
  const response = await authFetch(`${getBaseUrl()}/friends/requests/${requestUuid}/accept/`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  await loadFriendsData();
}

export async function declineFriendRequest(requestUuid: string): Promise<void> {
  const response = await authFetch(`${getBaseUrl()}/friends/requests/${requestUuid}/decline/`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  await loadFriendsData();
}

export async function removeFriendRelation(relationUuid: string): Promise<void> {
  const response = await authFetch(`${getBaseUrl()}/friends/${relationUuid}/`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  await loadFriendsData();
}

export async function searchUsers(query: string): Promise<UserSearchResult[]> {
  const normalized = query.trim();
  if (normalized.length < 2) {
    return [];
  }

  const response = await authFetch(
    `${getBaseUrl()}/users/search/?q=${encodeURIComponent(normalized)}`,
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const payload = (await response.json()) as UserSearchResult[];
  return payload.map((item) => mapUser(item));
}

export function resetFriendsState(): void {
  friends.set([]);
  incomingFriendRequests.set([]);
  outgoingFriendRequests.set([]);
  friendsLoading.set(false);
  friendsError.set(null);
}
