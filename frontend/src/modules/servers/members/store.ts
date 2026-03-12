import { get, writable } from 'svelte/store';
import { authFetch } from '../../../lib/auth';
import { getApiBaseUrl } from '../../../lib/url';
import type { ServerMemberItem, ServerMembersResponse } from '../../../types/gateway';
import type { MemberItem, MembersGroup, MembersQueryState } from './types';

const MEMBERS_CACHE_TTL_MS = 60_000;
const defaultQueryState: MembersQueryState = {
  fetchedAt: null,
  isLoading: false,
  error: null,
};

const inFlightByServer = new Map<string, Promise<void>>();

export const membersByServer = writable<Record<string, MembersGroup[]>>({});
export const membersQueryStateByServer = writable<Record<string, MembersQueryState>>({});

function getServerQueryState(serverUuid: string): MembersQueryState {
  return get(membersQueryStateByServer)[serverUuid] ?? defaultQueryState;
}

function patchServerQueryState(serverUuid: string, patch: Partial<MembersQueryState>): void {
  membersQueryStateByServer.update((current) => ({
    ...current,
    [serverUuid]: {
      ...(current[serverUuid] ?? defaultQueryState),
      ...patch,
    },
  }));
}

function normalizeMember(member: ServerMemberItem): MemberItem {
  return {
    uuid: member.uuid,
    displayName: member.displayName ?? member.display_name ?? 'Unknown user',
    isOnline: Boolean(member.isOnline ?? member.is_online ?? false),
    roles: member.roles ?? [],
    avatarUrl: member.avatarUrl ?? member.avatar_url ?? null,
    customStatus: member.customStatus ?? member.custom_status ?? null,
  };
}

function normalizeMembersPayload(payload: ServerMembersResponse): MembersGroup[] {
  const groups = Array.isArray(payload.groups) ? payload.groups : [];
  return groups.map((group) => ({
    key: group.key,
    label: group.label,
    members: (group.members ?? []).map(normalizeMember),
  }));
}

function isCacheFresh(serverUuid: string): boolean {
  const state = getServerQueryState(serverUuid);
  const hasCache = serverUuid in get(membersByServer);
  if (!hasCache || !state.fetchedAt) {
    return false;
  }
  return Date.now() - state.fetchedAt <= MEMBERS_CACHE_TTL_MS;
}

async function fetchServerMembers(serverUuid: string): Promise<MembersGroup[]> {
  const baseUrl = getApiBaseUrl();
  const response = await authFetch(`${baseUrl}/servers/${serverUuid}/members/`);
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`HTTP ${response.status} ${errorBody}`);
  }

  const payload = (await response.json()) as ServerMembersResponse;
  return normalizeMembersPayload(payload);
}

export async function ensureServerMembers(serverUuid: string, force = false): Promise<void> {
  if (!force && isCacheFresh(serverUuid)) {
    return;
  }
  const inFlightRequest = inFlightByServer.get(serverUuid);
  if (inFlightRequest) {
    await inFlightRequest;
    return;
  }

  patchServerQueryState(serverUuid, { isLoading: true, error: null });
  const request = (async () => {
    try {
      const groups = await fetchServerMembers(serverUuid);
      membersByServer.update((current) => ({ ...current, [serverUuid]: groups }));
      patchServerQueryState(serverUuid, {
        fetchedAt: Date.now(),
        isLoading: false,
        error: null,
      });
    } catch (error) {
      patchServerQueryState(serverUuid, {
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load members.',
      });
    } finally {
      inFlightByServer.delete(serverUuid);
    }
  })();

  inFlightByServer.set(serverUuid, request);
  await request;
}

export function updateServerMemberPresence(
  serverUuid: string,
  memberUuid: string,
  isOnline: boolean,
): boolean {
  let foundMember = false;
  membersByServer.update((current) => {
    const groups = current[serverUuid];
    if (!groups) {
      return current;
    }

    let changed = false;
    const nextGroups = groups.map((group) => ({
      ...group,
      members: group.members.map((member) => {
        if (member.uuid !== memberUuid) {
          return member;
        }
        foundMember = true;
        if (member.isOnline === isOnline) {
          return member;
        }
        changed = true;
        return { ...member, isOnline };
      }),
    }));

    if (!changed) {
      return current;
    }

    return {
      ...current,
      [serverUuid]: nextGroups,
    };
  });
  return foundMember;
}

export function resetMembersState(): void {
  membersByServer.set({});
  membersQueryStateByServer.set({});
  inFlightByServer.clear();
}
