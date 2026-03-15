import { authFetch } from '../../../lib/auth';
import { getApiBaseUrl, toApiAbsoluteUrl } from '../../../lib/url';
import type { FriendRequest, FriendUser, UserSearchResult } from '../../../types/gateway';

function mapUser<T extends FriendUser | UserSearchResult>(user: T): T {
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

export async function fetchFriendsData(): Promise<{
  friends: FriendUser[];
  incomingRequests: FriendRequest[];
  outgoingRequests: FriendRequest[];
}> {
  const [friendsRes, incomingRes, outgoingRes] = await Promise.all([
    authFetch(`${getApiBaseUrl()}/friends/`),
    authFetch(`${getApiBaseUrl()}/friends/requests/incoming/`),
    authFetch(`${getApiBaseUrl()}/friends/requests/outgoing/`),
  ]);

  if (!friendsRes.ok || !incomingRes.ok || !outgoingRes.ok) {
    throw new Error('Failed to load friends data.');
  }

  const friendsPayload = (await friendsRes.json()) as { uuid: string; user: FriendUser }[];
  const incomingPayload = (await incomingRes.json()) as FriendRequest[];
  const outgoingPayload = (await outgoingRes.json()) as FriendRequest[];

  const friends = friendsPayload
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

  return {
    friends,
    incomingRequests: incomingPayload.map(mapRequest),
    outgoingRequests: outgoingPayload.map(mapRequest),
  };
}

export async function postFriendRequest(userUuid: string): Promise<void> {
  const response = await authFetch(`${getApiBaseUrl()}/friends/requests/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_uuid: userUuid }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}

export async function postAcceptFriendRequest(requestUuid: string): Promise<void> {
  const response = await authFetch(`${getApiBaseUrl()}/friends/requests/${requestUuid}/accept/`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}

export async function postDeclineFriendRequest(requestUuid: string): Promise<void> {
  const response = await authFetch(`${getApiBaseUrl()}/friends/requests/${requestUuid}/decline/`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}

export async function deleteFriendRelation(relationUuid: string): Promise<void> {
  const response = await authFetch(`${getApiBaseUrl()}/friends/${relationUuid}/`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}

export async function searchUsersRequest(query: string): Promise<UserSearchResult[]> {
  const response = await authFetch(`${getApiBaseUrl()}/users/search/?q=${encodeURIComponent(query)}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const payload = (await response.json()) as UserSearchResult[];
  return payload.map((item) => mapUser(item));
}
