import { get, writable } from 'svelte/store';
import { authFetch } from '../../lib/auth';
import { toApiAbsoluteUrl } from '../../lib/url';
import { activeDMConversation } from '../../lib/stores/ui';
import type {
  DMConversation,
  DMMessage,
  DMMessageReadDto,
  PaginatedDMMessagesResponse,
} from '../../types/gateway';

type DMQueryState = {
  fetchedAt: number | null;
  isLoadingInitial: boolean;
  isLoadingOlder: boolean;
  isLoadingNewer: boolean;
  hasMoreOlder: boolean;
  hasMoreNewer: boolean;
  nextBefore: string | null;
  nextAfter: string | null;
  error: string | null;
};

const defaultQueryState: DMQueryState = {
  fetchedAt: null,
  isLoadingInitial: false,
  isLoadingOlder: false,
  isLoadingNewer: false,
  hasMoreOlder: true,
  hasMoreNewer: false,
  nextBefore: null,
  nextAfter: null,
  error: null,
};

const PAGE_LIMIT = 50;
const CACHE_TTL_MS = 60_000;

export const dmConversations = writable<DMConversation[]>([]);
export const dmMessagesByConversation = writable<Record<string, DMMessage[]>>({});
export const dmQueryStateByConversation = writable<Record<string, DMQueryState>>({});

const inFlightInitial: Record<string, Promise<void> | undefined> = {};
const inFlightOlder: Record<string, Promise<void> | undefined> = {};
const inFlightNewer: Record<string, Promise<void> | undefined> = {};
let inFlightConversations: Promise<void> | null = null;

function getBaseUrl(): string {
  const base = import.meta.env.VITE_API_URL;
  if (!base) {
    throw new Error('Missing VITE_API_URL.');
  }
  return base;
}

function patchQueryState(conversationUuid: string, patch: Partial<DMQueryState>): void {
  dmQueryStateByConversation.update((current) => ({
    ...current,
    [conversationUuid]: {
      ...(current[conversationUuid] ?? defaultQueryState),
      ...patch,
    },
  }));
}

function mapDMMessage(conversationUuid: string, item: DMMessageReadDto): DMMessage {
  return {
    uuid: item.uuid,
    conversation_uuid: item.conversationUuid ?? item.conversation_uuid ?? conversationUuid,
    channel_uuid: item.conversationUuid ?? item.conversation_uuid ?? conversationUuid,
    content: item.content,
    author:
      item.authorProfileDisplayName ?? item.author_profile_display_name ?? String(item.author ?? ''),
    author_uuid: String(item.author),
    avatar_url: toApiAbsoluteUrl(item.avatarUrl ?? item.avatar_url ?? null),
    is_deleted: Boolean(item.isDeleted ?? item.is_deleted ?? false),
    is_edited: Boolean(item.isEdited ?? item.is_edited ?? false),
    edited_at: item.editedAt ?? item.edited_at ?? null,
    reactions: (item.reactions ?? []).map((reaction) => ({
      emoji: reaction.emoji,
      count: Number(reaction.count ?? 0),
      reacted_by_me: Boolean(reaction.reactedByMe ?? reaction.reacted_by_me ?? false),
    })),
    ciphertext: item.ciphertext ?? null,
    nonce: item.nonce ?? null,
    encryption_version: item.encryptionVersion ?? item.encryption_version ?? null,
    sender_key_id: item.senderKeyId ?? item.sender_key_id ?? null,
    created_at: item.createdAt ?? item.created_at,
    updated_at: item.updatedAt ?? item.updated_at,
  };
}

function mapConversation(item: DMConversation): DMConversation {
  return {
    ...item,
    avatar_url: toApiAbsoluteUrl(item.avatarUrl ?? item.avatar_url ?? null),
    participants: (item.participants ?? []).map((participant) => ({
      ...participant,
      avatar_url: toApiAbsoluteUrl(participant.avatarUrl ?? participant.avatar_url ?? null),
    })),
    last_message: item.lastMessage ?? item.last_message ?? null,
  };
}

function sortConversations(conversations: DMConversation[]): DMConversation[] {
  return [...conversations].sort(
    (a, b) =>
      new Date(b.updatedAt ?? b.updated_at ?? 0).getTime() -
      new Date(a.updatedAt ?? a.updated_at ?? 0).getTime(),
  );
}

function upsertConversation(conversation: DMConversation): void {
  dmConversations.update((current) => {
    const idx = current.findIndex((item) => item.uuid === conversation.uuid);
    if (idx === -1) {
      return sortConversations([...current, conversation]);
    }
    const next = [...current];
    next[idx] = {
      ...next[idx],
      ...conversation,
    };
    return sortConversations(next);
  });
}

function normalizeMessagesPayload(raw: unknown): PaginatedDMMessagesResponse {
  if (Array.isArray(raw)) {
    return {
      items: raw as DMMessageReadDto[],
      has_more_older: false,
      has_more_newer: false,
      next_before: null,
      next_after: null,
    };
  }
  return (raw ?? {}) as PaginatedDMMessagesResponse;
}

function dedupeByUuid(messages: DMMessage[]): DMMessage[] {
  const seen = new Set<string>();
  const result: DMMessage[] = [];
  for (const message of messages) {
    if (seen.has(message.uuid)) {
      continue;
    }
    seen.add(message.uuid);
    result.push(message);
  }
  return result;
}

function isFresh(conversationUuid: string): boolean {
  const state = get(dmQueryStateByConversation)[conversationUuid] ?? defaultQueryState;
  const hasData = conversationUuid in get(dmMessagesByConversation);
  if (!hasData || !state.fetchedAt) {
    return false;
  }
  return Date.now() - state.fetchedAt <= CACHE_TTL_MS;
}

export async function ensureDMConversations(force = false): Promise<void> {
  if (inFlightConversations && !force) {
    return inFlightConversations;
  }

  const run = (async () => {
    const response = await authFetch(`${getBaseUrl()}/dm/conversations/`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = (await response.json()) as DMConversation[];
    dmConversations.set(sortConversations(data.map(mapConversation)));
  })();

  inFlightConversations = run;
  try {
    await run;
  } finally {
    inFlightConversations = null;
  }
}

async function fetchDMMessagesPage(
  conversationUuid: string,
  options: { before?: string | null; after?: string | null },
): Promise<PaginatedDMMessagesResponse> {
  const params = new URLSearchParams({
    limit: String(PAGE_LIMIT),
  });
  if (options.before) {
    params.set('before', options.before);
  }
  if (options.after) {
    params.set('after', options.after);
  }

  const response = await authFetch(
    `${getBaseUrl()}/dm/conversations/${conversationUuid}/messages/?${params.toString()}`,
  );
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status} ${body}`);
  }

  return normalizeMessagesPayload(await response.json());
}

function mergeMessages(
  existing: DMMessage[],
  incoming: DMMessage[],
  direction: 'initial' | 'older' | 'newer',
): DMMessage[] {
  if (direction === 'initial') {
    return dedupeByUuid(incoming);
  }
  const merged = direction === 'older' ? [...incoming, ...existing] : [...existing, ...incoming];
  return dedupeByUuid(merged);
}

async function runFetch(conversationUuid: string, direction: 'initial' | 'older' | 'newer'): Promise<void> {
  const state = get(dmQueryStateByConversation)[conversationUuid] ?? defaultQueryState;
  const payload = await fetchDMMessagesPage(conversationUuid, {
    before: direction === 'older' ? state.nextBefore : null,
    after: direction === 'newer' ? state.nextAfter : null,
  });

  const mapped = (payload.items ?? []).map((item) => mapDMMessage(conversationUuid, item));

  dmMessagesByConversation.update((current) => {
    const existing = current[conversationUuid] ?? [];
    const merged = mergeMessages(existing, mapped, direction);
    return {
      ...current,
      [conversationUuid]: merged,
    };
  });

  patchQueryState(conversationUuid, {
    fetchedAt: Date.now(),
    hasMoreOlder: Boolean(payload.hasMoreOlder ?? payload.has_more_older ?? false),
    hasMoreNewer: Boolean(payload.hasMoreNewer ?? payload.has_more_newer ?? false),
    nextBefore: payload.nextBefore ?? payload.next_before ?? null,
    nextAfter: payload.nextAfter ?? payload.next_after ?? null,
    error: null,
  });
}

export async function ensureDMMessages(conversationUuid: string): Promise<void> {
  if (isFresh(conversationUuid)) {
    return;
  }
  if (inFlightInitial[conversationUuid]) {
    return inFlightInitial[conversationUuid];
  }

  patchQueryState(conversationUuid, { isLoadingInitial: true, error: null });
  const run = runFetch(conversationUuid, 'initial')
    .catch((error) => {
      patchQueryState(conversationUuid, {
        error: error instanceof Error ? error.message : 'Failed to load messages.',
      });
    })
    .finally(() => {
      patchQueryState(conversationUuid, { isLoadingInitial: false });
      delete inFlightInitial[conversationUuid];
    });

  inFlightInitial[conversationUuid] = run;
  return run;
}

export async function loadOlderDMMessages(conversationUuid: string): Promise<void> {
  const state = get(dmQueryStateByConversation)[conversationUuid] ?? defaultQueryState;
  if (inFlightOlder[conversationUuid] || !state.hasMoreOlder || !state.nextBefore) {
    return;
  }

  patchQueryState(conversationUuid, { isLoadingOlder: true, error: null });
  const run = runFetch(conversationUuid, 'older')
    .catch((error) => {
      patchQueryState(conversationUuid, {
        error: error instanceof Error ? error.message : 'Failed to load older messages.',
      });
    })
    .finally(() => {
      patchQueryState(conversationUuid, { isLoadingOlder: false });
      delete inFlightOlder[conversationUuid];
    });

  inFlightOlder[conversationUuid] = run;
  return run;
}

export async function loadNewerDMMessages(conversationUuid: string): Promise<void> {
  const state = get(dmQueryStateByConversation)[conversationUuid] ?? defaultQueryState;
  if (inFlightNewer[conversationUuid] || !state.hasMoreNewer || !state.nextAfter) {
    return;
  }

  patchQueryState(conversationUuid, { isLoadingNewer: true, error: null });
  const run = runFetch(conversationUuid, 'newer')
    .catch((error) => {
      patchQueryState(conversationUuid, {
        error: error instanceof Error ? error.message : 'Failed to load newer messages.',
      });
    })
    .finally(() => {
      patchQueryState(conversationUuid, { isLoadingNewer: false });
      delete inFlightNewer[conversationUuid];
    });

  inFlightNewer[conversationUuid] = run;
  return run;
}

export function addDMMessage(message: DMMessage): void {
  dmMessagesByConversation.update((current) => {
    const existing = current[message.conversation_uuid] ?? [];
    const merged = dedupeByUuid([...existing, message]);
    return {
      ...current,
      [message.conversation_uuid]: merged,
    };
  });
  patchQueryState(message.conversation_uuid, {
    fetchedAt: Date.now(),
    nextAfter: message.created_at ? `${message.created_at}|${message.uuid}` : null,
    error: null,
  });
}

export function updateDMMessage(message: DMMessage): void {
  dmMessagesByConversation.update((current) => {
    const existing = current[message.conversation_uuid] ?? [];
    return {
      ...current,
      [message.conversation_uuid]: existing.map((item) => (item.uuid === message.uuid ? { ...item, ...message } : item)),
    };
  });
}

export function softDeleteDMMessage(message: DMMessage): void {
  updateDMMessage({ ...message, content: '', is_deleted: true });
}

export async function sendDMMessageViaRest(
  conversationUuid: string,
  content: string,
): Promise<DMMessage> {
  const response = await authFetch(`${getBaseUrl()}/dm/conversations/${conversationUuid}/messages/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status} ${body}`);
  }

  const dto = (await response.json()) as DMMessageReadDto;
  const mapped = mapDMMessage(conversationUuid, dto);
  addDMMessage(mapped);
  return mapped;
}

export async function markDMConversationAsRead(conversationUuid: string, lastReadMessageUuid?: string): Promise<void> {
  await authFetch(`${getBaseUrl()}/dm/conversations/${conversationUuid}/read-state/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...(lastReadMessageUuid ? { last_read_message_uuid: lastReadMessageUuid } : {}),
    }),
  });
}

export async function createDMConversation(
  participantUuids: string[],
  title?: string,
): Promise<DMConversation> {
  const normalizedParticipants = Array.from(
    new Set(participantUuids.map((item) => item.trim()).filter(Boolean)),
  );
  if (normalizedParticipants.length === 0) {
    throw new Error('At least one participant is required.');
  }

  const response = await authFetch(`${getBaseUrl()}/dm/conversations/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      participant_uuids: normalizedParticipants,
      ...(title?.trim() ? { title: title.trim() } : {}),
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status} ${body}`);
  }

  const dto = (await response.json()) as DMConversation;
  const mapped = mapConversation(dto);
  upsertConversation(mapped);
  return mapped;
}

export async function openDirectConversation(userUuid: string): Promise<DMConversation> {
  const response = await authFetch(`${getBaseUrl()}/dm/conversations/direct/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_uuid: userUuid }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status} ${body}`);
  }

  const dto = (await response.json()) as DMConversation;
  const mapped = mapConversation(dto);
  upsertConversation(mapped);
  activeDMConversation.set(mapped);
  return mapped;
}

export function updateDMConversationPreview(conversationUuid: string, message: DMMessage): void {
  dmConversations.update((current) => {
    const next = current.map((conversation) => {
      if (conversation.uuid !== conversationUuid) {
        return conversation;
      }
      return {
        ...conversation,
        last_message: message,
        updated_at: message.created_at,
      };
    });
    return sortConversations(next);
  });
}

export function incrementDMUnread(conversationUuid: string): void {
  dmConversations.update((current) =>
    current.map((conversation) => {
      if (conversation.uuid !== conversationUuid) {
        return conversation;
      }
      const unread = Number(conversation.unreadCount ?? conversation.unread_count ?? 0) + 1;
      return {
        ...conversation,
        unread_count: unread,
      };
    }),
  );
}

export function clearDMUnread(conversationUuid: string): void {
  dmConversations.update((current) =>
    current.map((conversation) =>
      conversation.uuid === conversationUuid
        ? {
            ...conversation,
            unread_count: 0,
          }
        : conversation,
    ),
  );
}

export function resetDMState(): void {
  dmConversations.set([]);
  dmMessagesByConversation.set({});
  dmQueryStateByConversation.set({});
}
