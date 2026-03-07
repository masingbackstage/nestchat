import { get, writable } from 'svelte/store';
import type { Message, MessageReadDto, PaginatedMessagesResponse } from '../../types/gateway';

type MessagesByChannel = Record<string, Message[]>;

type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error';
type ChannelQueryState = {
  fetchedAt: number | null;
  isLoadingInitial: boolean;
  isLoadingOlder: boolean;
  isLoadingNewer: boolean;
  hasMoreOlder: boolean;
  hasMoreNewer: boolean;
  nextBefore: string | null;
  nextAfter: string | null;
  wasOlderTrimmed: boolean;
  wasNewerTrimmed: boolean;
  error: string | null;
};

type NormalizedPaginatedPayload = {
  items: MessageReadDto[];
  hasMoreOlder: boolean;
  hasMoreNewer: boolean;
  nextBefore: string | null;
  nextAfter: string | null;
};

type FetchDirection = 'initial' | 'older' | 'newer';

const PAGE_LIMIT = 50;
const CHANNEL_MESSAGES_CACHE_TTL_MS = 60_000;
export const MAX_MESSAGES_PER_CHANNEL = 300;

const defaultQueryState: ChannelQueryState = {
  fetchedAt: null,
  isLoadingInitial: false,
  isLoadingOlder: false,
  isLoadingNewer: false,
  hasMoreOlder: true,
  hasMoreNewer: false,
  nextBefore: null,
  nextAfter: null,
  wasOlderTrimmed: false,
  wasNewerTrimmed: false,
  error: null,
};

export const messagesByChannel = writable<MessagesByChannel>({});
export const chatConnectionStatus = writable<ConnectionStatus>('idle');
export const channelQueryStateById = writable<Record<string, ChannelQueryState>>({});
export const unreadCountByChannel = writable<Record<string, number>>({});

const inFlightInitialByChannel: Record<string, Promise<void> | undefined> = {};
const inFlightOlderByChannel: Record<string, Promise<void> | undefined> = {};
const inFlightNewerByChannel: Record<string, Promise<void> | undefined> = {};
const requestIdCounterByChannel: Record<string, number> = {};

function getToken(): string | null {
  return import.meta.env.VITE_API_TOKEN ?? localStorage.getItem('access_token');
}

function getBaseUrl(): string | null {
  return import.meta.env.VITE_API_URL ?? null;
}

function getChannelState(channelUuid: string): ChannelQueryState {
  return get(channelQueryStateById)[channelUuid] ?? defaultQueryState;
}

function patchChannelState(channelUuid: string, patch: Partial<ChannelQueryState>): void {
  channelQueryStateById.update((current) => ({
    ...current,
    [channelUuid]: {
      ...(current[channelUuid] ?? defaultQueryState),
      ...patch,
    },
  }));
}

function mapApiMessages(channelUuid: string, items: MessageReadDto[]): Message[] {
  return items.map((item) => ({
    uuid: item.uuid,
    channel_uuid: channelUuid,
    content: item.content,
    author: item.authorProfileDisplayName ?? item.author_profile_display_name ?? String(item.author),
    created_at: item.createdAt ?? item.created_at,
  }));
}

function normalizePaginatedPayload(raw: unknown): NormalizedPaginatedPayload {
  if (Array.isArray(raw)) {
    return {
      items: raw as MessageReadDto[],
      hasMoreOlder: false,
      hasMoreNewer: false,
      nextBefore: null,
      nextAfter: null,
    };
  }

  const payload = raw as Partial<PaginatedMessagesResponse>;
  return {
    items: Array.isArray(payload.items) ? payload.items : [],
    hasMoreOlder: Boolean(payload.hasMoreOlder ?? payload.has_more_older ?? false),
    hasMoreNewer: Boolean(payload.hasMoreNewer ?? payload.has_more_newer ?? false),
    nextBefore: payload.nextBefore ?? payload.next_before ?? null,
    nextAfter: payload.nextAfter ?? payload.next_after ?? null,
  };
}

function dedupeByUuid(messages: Message[]): Message[] {
  const seen = new Set<string>();
  const result: Message[] = [];
  for (const message of messages) {
    if (seen.has(message.uuid)) {
      continue;
    }
    seen.add(message.uuid);
    result.push(message);
  }
  return result;
}

function getEdgeMessage(messages: Message[], edge: 'oldest' | 'newest'): Message | null {
  if (messages.length === 0) {
    return null;
  }

  const message = edge === 'oldest' ? messages[0] : messages[messages.length - 1];
  return message ?? null;
}

function buildCursorFromMessage(message: Message | null): string | null {
  if (!message?.created_at) {
    return null;
  }

  return `${message.created_at}|${message.uuid}`;
}

function applyWindowLimit(
  messages: Message[],
  direction: FetchDirection,
): {
  windowed: Message[];
  trimmedOlder: boolean;
  trimmedNewer: boolean;
} {
  if (messages.length <= MAX_MESSAGES_PER_CHANNEL) {
    return {
      windowed: messages,
      trimmedOlder: false,
      trimmedNewer: false,
    };
  }

  if (direction === 'older') {
    return {
      windowed: messages.slice(0, MAX_MESSAGES_PER_CHANNEL),
      trimmedOlder: false,
      trimmedNewer: true,
    };
  }

  return {
    windowed: messages.slice(messages.length - MAX_MESSAGES_PER_CHANNEL),
    trimmedOlder: true,
    trimmedNewer: false,
  };
}

function isCacheFresh(channelUuid: string): boolean {
  const state = getChannelState(channelUuid);
  const hasCache = channelUuid in get(messagesByChannel);
  if (!hasCache || !state.fetchedAt) {
    return false;
  }

  return Date.now() - state.fetchedAt <= CHANNEL_MESSAGES_CACHE_TTL_MS;
}

async function fetchMessagesPage(
  channelUuid: string,
  options: {
    before?: string | null;
    after?: string | null;
  },
): Promise<NormalizedPaginatedPayload> {
  const baseUrl = getBaseUrl();
  const token = getToken();

  if (!baseUrl) {
    throw new Error('Brak VITE_API_URL.');
  }

  const params = new URLSearchParams({
    channel_uuid: channelUuid,
    limit: String(PAGE_LIMIT),
  });
  if (options.before) {
    params.set('before', options.before);
  }
  if (options.after) {
    params.set('after', options.after);
  }

  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
  const response = await fetch(`${baseUrl}/chat/messages/?${params.toString()}`, { headers });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`HTTP ${response.status} ${errorBody}`);
  }

  const rawData = (await response.json()) as unknown;
  return normalizePaginatedPayload(rawData);
}

function mergeMessagesByDirection(
  existing: Message[],
  incoming: Message[],
  direction: FetchDirection,
): {
  merged: Message[];
  trimmedOlder: boolean;
  trimmedNewer: boolean;
} {
  if (direction === 'initial') {
    const deduped = dedupeByUuid(incoming);
    return {
      merged: deduped,
      trimmedOlder: false,
      trimmedNewer: false,
    };
  }

  const combined = direction === 'older' ? [...incoming, ...existing] : [...existing, ...incoming];
  const deduped = dedupeByUuid(combined);
  const windowed = applyWindowLimit(deduped, direction);

  return {
    merged: windowed.windowed,
    trimmedOlder: windowed.trimmedOlder,
    trimmedNewer: windowed.trimmedNewer,
  };
}

function updateChannelStateAfterFetch(
  channelUuid: string,
  direction: FetchDirection,
  responseMeta: NormalizedPaginatedPayload,
  mergedMessages: Message[],
  trimmedOlderNow: boolean,
  trimmedNewerNow: boolean,
): void {
  const previousState = getChannelState(channelUuid);
  const oldestEdgeMessage = getEdgeMessage(mergedMessages, 'oldest');
  const newestEdgeMessage = getEdgeMessage(mergedMessages, 'newest');
  const oldestEdgeCursor = buildCursorFromMessage(oldestEdgeMessage);
  const newestEdgeCursor = buildCursorFromMessage(newestEdgeMessage);

  let wasOlderTrimmed = previousState.wasOlderTrimmed;
  let wasNewerTrimmed = previousState.wasNewerTrimmed;

  if (trimmedOlderNow) {
    wasOlderTrimmed = true;
  } else if (direction === 'older' && !responseMeta.hasMoreOlder) {
    wasOlderTrimmed = false;
  }

  if (trimmedNewerNow) {
    wasNewerTrimmed = true;
  } else if (direction === 'newer' && !responseMeta.hasMoreNewer) {
    wasNewerTrimmed = false;
  }

  const hasMoreOlder = responseMeta.hasMoreOlder || wasOlderTrimmed;
  const hasMoreNewer = responseMeta.hasMoreNewer || wasNewerTrimmed;

  patchChannelState(channelUuid, {
    isLoadingInitial: false,
    isLoadingOlder: false,
    isLoadingNewer: false,
    hasMoreOlder,
    hasMoreNewer,
    nextBefore: hasMoreOlder
      ? wasOlderTrimmed
        ? oldestEdgeCursor ?? responseMeta.nextBefore
        : responseMeta.hasMoreOlder
          ? responseMeta.nextBefore
          : oldestEdgeCursor ?? responseMeta.nextBefore
      : null,
    nextAfter: hasMoreNewer
      ? wasNewerTrimmed
        ? newestEdgeCursor ?? responseMeta.nextAfter
        : responseMeta.hasMoreNewer
          ? responseMeta.nextAfter
          : newestEdgeCursor ?? responseMeta.nextAfter
      : null,
    wasOlderTrimmed,
    wasNewerTrimmed,
    error: null,
    fetchedAt: Date.now(),
  });
}

async function fetchAndMerge(
  channelUuid: string,
  direction: FetchDirection,
  options: {
    before?: string | null;
    after?: string | null;
  },
): Promise<void> {
  const normalized = await fetchMessagesPage(channelUuid, options);
  const mappedMessages = mapApiMessages(channelUuid, normalized.items);

  const existing = get(messagesByChannel)[channelUuid] ?? [];
  const mergedState = mergeMessagesByDirection(existing, mappedMessages, direction);

  messagesByChannel.update((current) => ({
    ...current,
    [channelUuid]: mergedState.merged,
  }));

  updateChannelStateAfterFetch(
    channelUuid,
    direction,
    normalized,
    mergedState.merged,
    mergedState.trimmedOlder,
    mergedState.trimmedNewer,
  );
}

async function fetchInitialMessages(channelUuid: string, background: boolean): Promise<void> {
  if (inFlightInitialByChannel[channelUuid]) {
    return inFlightInitialByChannel[channelUuid];
  }

  requestIdCounterByChannel[channelUuid] = (requestIdCounterByChannel[channelUuid] ?? 0) + 1;
  const requestId = requestIdCounterByChannel[channelUuid];

  patchChannelState(channelUuid, {
    isLoadingInitial: !background,
    error: null,
  });

  const task = (async () => {
    try {
      await fetchAndMerge(channelUuid, 'initial', {});
    } catch (error) {
      const currentId = requestIdCounterByChannel[channelUuid];
      if (currentId !== requestId) {
        return;
      }

      patchChannelState(channelUuid, {
        isLoadingInitial: false,
        error: error instanceof Error ? error.message : 'Błąd ładowania wiadomości.',
      });
    } finally {
      inFlightInitialByChannel[channelUuid] = undefined;
    }
  })();

  inFlightInitialByChannel[channelUuid] = task;
  return task;
}

export async function ensureChannelMessages(channelUuid: string): Promise<void> {
  const hasCache = channelUuid in get(messagesByChannel);
  const inFlight = inFlightInitialByChannel[channelUuid];

  if (inFlight) {
    return inFlight;
  }

  if (!hasCache) {
    await fetchInitialMessages(channelUuid, false);
    return;
  }

  if (isCacheFresh(channelUuid)) {
    return;
  }

  void fetchInitialMessages(channelUuid, true);
}

function getLatestMessageCursor(channelUuid: string): string | null {
  const messages = get(messagesByChannel)[channelUuid] ?? [];
  return buildCursorFromMessage(getEdgeMessage(messages, 'newest'));
}

export async function loadOlderMessages(channelUuid: string): Promise<void> {
  const state = getChannelState(channelUuid);
  const inFlight = inFlightOlderByChannel[channelUuid];
  if (inFlight || !state.hasMoreOlder || !state.nextBefore) {
    return inFlight;
  }

  patchChannelState(channelUuid, {
    isLoadingOlder: true,
    error: null,
  });

  const task = (async () => {
    try {
      await fetchAndMerge(channelUuid, 'older', {
        before: state.nextBefore,
      });
    } catch (error) {
      patchChannelState(channelUuid, {
        isLoadingOlder: false,
        error: error instanceof Error ? error.message : 'Błąd ładowania starszych wiadomości.',
      });
    } finally {
      inFlightOlderByChannel[channelUuid] = undefined;
    }
  })();

  inFlightOlderByChannel[channelUuid] = task;
  return task;
}

export async function loadNewerMessages(channelUuid: string): Promise<void> {
  const state = getChannelState(channelUuid);
  const inFlight = inFlightNewerByChannel[channelUuid];
  if (inFlight || !state.hasMoreNewer || !state.nextAfter) {
    return inFlight;
  }

  patchChannelState(channelUuid, {
    isLoadingNewer: true,
    error: null,
  });

  const task = (async () => {
    try {
      await fetchAndMerge(channelUuid, 'newer', {
        after: state.nextAfter,
      });
    } catch (error) {
      patchChannelState(channelUuid, {
        isLoadingNewer: false,
        error: error instanceof Error ? error.message : 'Błąd ładowania nowszych wiadomości.',
      });
    } finally {
      inFlightNewerByChannel[channelUuid] = undefined;
    }
  })();

  inFlightNewerByChannel[channelUuid] = task;
  return task;
}

export async function syncChannelFromLatestCursor(channelUuid: string): Promise<void> {
  const inFlight = inFlightNewerByChannel[channelUuid];
  if (inFlight) {
    return inFlight;
  }

  const afterCursor = getLatestMessageCursor(channelUuid);
  if (!afterCursor) {
    return;
  }

  patchChannelState(channelUuid, {
    isLoadingNewer: true,
    error: null,
  });

  const task = (async () => {
    try {
      await fetchAndMerge(channelUuid, 'newer', {
        after: afterCursor,
      });
    } catch (error) {
      patchChannelState(channelUuid, {
        isLoadingNewer: false,
        error: error instanceof Error ? error.message : 'Błąd synchronizacji wiadomości.',
      });
    } finally {
      inFlightNewerByChannel[channelUuid] = undefined;
    }
  })();

  inFlightNewerByChannel[channelUuid] = task;
  return task;
}

export function incrementUnreadCount(channelUuid: string): void {
  unreadCountByChannel.update((current) => ({
    ...current,
    [channelUuid]: (current[channelUuid] ?? 0) + 1,
  }));
}

export function setUnreadCount(channelUuid: string, unreadCount: number): void {
  unreadCountByChannel.update((current) => ({
    ...current,
    [channelUuid]: Math.max(0, unreadCount),
  }));
}

export async function fetchChannelReadState(channelUuid: string): Promise<void> {
  const baseUrl = getBaseUrl();
  const token = getToken();
  if (!baseUrl || !token) {
    return;
  }

  const params = new URLSearchParams({ channel_uuid: channelUuid });
  const response = await fetch(`${baseUrl}/chat/read-state/?${params.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    return;
  }

  const payload = (await response.json()) as {
    unreadCount?: number;
    unread_count?: number;
  };
  const unread = Number(payload.unreadCount ?? payload.unread_count ?? 0);
  setUnreadCount(channelUuid, unread);
}

export async function markChannelAsRead(
  channelUuid: string,
  lastReadMessageUuid?: string,
): Promise<void> {
  const baseUrl = getBaseUrl();
  const token = getToken();
  if (!baseUrl || !token) {
    return;
  }

  const body: Record<string, string> = { channel_uuid: channelUuid };
  if (lastReadMessageUuid) {
    body.last_read_message_uuid = lastReadMessageUuid;
  }

  const response = await fetch(`${baseUrl}/chat/read-state/`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    return;
  }

  setUnreadCount(channelUuid, 0);
}

export function addMessage(message: Message): void {
  const currentMessages = get(messagesByChannel)[message.channel_uuid] ?? [];
  if (currentMessages.some((item) => item.uuid === message.uuid)) {
    return;
  }

  const merged = dedupeByUuid([...currentMessages, message]);
  const windowed = applyWindowLimit(merged, 'newer');

  messagesByChannel.update((current) => ({
    ...current,
    [message.channel_uuid]: windowed.windowed,
  }));

  const previousState = getChannelState(message.channel_uuid);
  const oldestCursor = buildCursorFromMessage(getEdgeMessage(windowed.windowed, 'oldest'));
  const newestCursor = buildCursorFromMessage(getEdgeMessage(windowed.windowed, 'newest'));
  const wasOlderTrimmed = previousState.wasOlderTrimmed || windowed.trimmedOlder;

  patchChannelState(message.channel_uuid, {
    fetchedAt: Date.now(),
    hasMoreOlder: previousState.hasMoreOlder || wasOlderTrimmed,
    nextBefore:
      previousState.hasMoreOlder || wasOlderTrimmed
        ? oldestCursor ?? previousState.nextBefore
        : previousState.nextBefore,
    hasMoreNewer: false,
    nextAfter: newestCursor,
    wasOlderTrimmed,
    wasNewerTrimmed: false,
    error: null,
  });
}

export function setMessagesForChannel(channelUuid: string, messages: Message[]): void {
  const deduped = dedupeByUuid(messages);
  const windowed = applyWindowLimit(deduped, 'newer').windowed;

  messagesByChannel.update((current) => ({
    ...current,
    [channelUuid]: windowed,
  }));
}

export function clearMessagesForChannel(channelUuid: string): void {
  messagesByChannel.update((current) => ({
    ...current,
    [channelUuid]: [],
  }));

  patchChannelState(channelUuid, {
    fetchedAt: null,
    isLoadingInitial: false,
    isLoadingOlder: false,
    isLoadingNewer: false,
    hasMoreOlder: true,
    hasMoreNewer: false,
    nextBefore: null,
    nextAfter: null,
    wasOlderTrimmed: false,
    wasNewerTrimmed: false,
    error: null,
  });

  unreadCountByChannel.update((current) => ({
    ...current,
    [channelUuid]: 0,
  }));
}
