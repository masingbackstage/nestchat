import { get, writable } from 'svelte/store';
import type { Message } from '../../../types/gateway';
import { fetchChannelReadStatePayload, fetchMessagesPage, postChannelReadState } from './api';
import type {
  ChannelQueryState,
  ConnectionStatus,
  FetchDirection,
  MessagesByChannel,
} from './types';
import { defaultChannelQueryState } from './types';
import {
  applyWindowLimit,
  buildCursorFromMessage,
  dedupeByUuid,
  getEdgeMessage,
  isChannelCacheFresh,
  mapApiMessages,
  MAX_MESSAGES_PER_CHANNEL,
  mergeMessagesByDirection,
} from './utils';

export { MAX_MESSAGES_PER_CHANNEL };

export const messagesByChannel = writable<MessagesByChannel>({});
export const chatConnectionStatus = writable<ConnectionStatus>('idle');
export const channelQueryStateById = writable<Record<string, ChannelQueryState>>({});
export const unreadCountByChannel = writable<Record<string, number>>({});
export const lastReadMessageUuidByChannel = writable<Record<string, string | null>>({});

const inFlightInitialByChannel = new Map<string, Promise<void>>();
const inFlightOlderByChannel = new Map<string, Promise<void>>();
const inFlightNewerByChannel = new Map<string, Promise<void>>();
const requestIdCounterByChannel = new Map<string, number>();
const deliveredClientIdsByChannel = new Map<string, Set<string>>();

function getChannelState(channelUuid: string): ChannelQueryState {
  return get(channelQueryStateById)[channelUuid] ?? defaultChannelQueryState;
}

function patchChannelState(channelUuid: string, patch: Partial<ChannelQueryState>): void {
  channelQueryStateById.update((current) => ({
    ...current,
    [channelUuid]: {
      ...(current[channelUuid] ?? defaultChannelQueryState),
      ...patch,
    },
  }));
}

function markClientIdDelivered(channelUuid: string, clientId: string): void {
  const deliveredSet = deliveredClientIdsByChannel.get(channelUuid) ?? new Set<string>();
  deliveredSet.add(clientId);

  if (deliveredSet.size > 500) {
    const first = deliveredSet.values().next().value;
    if (first) {
      deliveredSet.delete(first);
    }
  }

  deliveredClientIdsByChannel.set(channelUuid, deliveredSet);
}

export function wasClientIdDelivered(channelUuid: string, clientId: string): boolean {
  return deliveredClientIdsByChannel.get(channelUuid)?.has(clientId) ?? false;
}

function resolveMessageStateAfterAppend(channelUuid: string, messages: Message[]): void {
  const previousState = getChannelState(channelUuid);
  const oldestCursor = buildCursorFromMessage(getEdgeMessage(messages, 'oldest'));
  const newestCursor = buildCursorFromMessage(getEdgeMessage(messages, 'newest'));
  const hasPending = messages.some((msg) => msg.pending);

  patchChannelState(channelUuid, {
    fetchedAt: Date.now(),
    hasMoreOlder: previousState.hasMoreOlder || previousState.wasOlderTrimmed,
    nextBefore:
      previousState.hasMoreOlder || previousState.wasOlderTrimmed
        ? (oldestCursor ?? previousState.nextBefore)
        : previousState.nextBefore,
    hasMoreNewer: hasPending ? true : previousState.hasMoreNewer,
    nextAfter: newestCursor ?? previousState.nextAfter,
    wasOlderTrimmed: previousState.wasOlderTrimmed,
    wasNewerTrimmed: previousState.wasNewerTrimmed,
    error: null,
  });
}

function isCacheFresh(channelUuid: string): boolean {
  const hasCache = channelUuid in get(messagesByChannel);
  return isChannelCacheFresh(hasCache, getChannelState(channelUuid));
}

function updateChannelStateAfterFetch(
  channelUuid: string,
  direction: FetchDirection,
  responseMeta: Awaited<ReturnType<typeof fetchMessagesPage>>,
  mergedMessages: Message[],
  trimmedOlderNow: boolean,
  trimmedNewerNow: boolean,
): void {
  const previousState = getChannelState(channelUuid);
  const oldestEdgeCursor = buildCursorFromMessage(getEdgeMessage(mergedMessages, 'oldest'));
  const newestEdgeCursor = buildCursorFromMessage(getEdgeMessage(mergedMessages, 'newest'));

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
        ? (oldestEdgeCursor ?? responseMeta.nextBefore)
        : responseMeta.hasMoreOlder
          ? responseMeta.nextBefore
          : (oldestEdgeCursor ?? responseMeta.nextBefore)
      : null,
    nextAfter: hasMoreNewer
      ? wasNewerTrimmed
        ? (newestEdgeCursor ?? responseMeta.nextAfter)
        : responseMeta.hasMoreNewer
          ? responseMeta.nextAfter
          : (newestEdgeCursor ?? responseMeta.nextAfter)
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
  const inFlight = inFlightInitialByChannel.get(channelUuid);
  if (inFlight) {
    return inFlight;
  }

  const requestId = (requestIdCounterByChannel.get(channelUuid) ?? 0) + 1;
  requestIdCounterByChannel.set(channelUuid, requestId);

  patchChannelState(channelUuid, {
    isLoadingInitial: !background,
    error: null,
  });

  const task = (async () => {
    try {
      await fetchAndMerge(channelUuid, 'initial', {});
    } catch (error) {
      const currentId = requestIdCounterByChannel.get(channelUuid);
      if (currentId !== requestId) {
        return;
      }

      patchChannelState(channelUuid, {
        isLoadingInitial: false,
        error: error instanceof Error ? error.message : 'Failed to load messages.',
      });
    } finally {
      inFlightInitialByChannel.delete(channelUuid);
    }
  })();

  inFlightInitialByChannel.set(channelUuid, task);
  return task;
}

export async function ensureChannelMessages(channelUuid: string): Promise<void> {
  const hasCache = channelUuid in get(messagesByChannel);
  const inFlight = inFlightInitialByChannel.get(channelUuid);

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
  const inFlight = inFlightOlderByChannel.get(channelUuid);
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
        error: error instanceof Error ? error.message : 'Failed to load older messages.',
      });
    } finally {
      inFlightOlderByChannel.delete(channelUuid);
    }
  })();

  inFlightOlderByChannel.set(channelUuid, task);
  return task;
}

export async function loadNewerMessages(channelUuid: string): Promise<void> {
  const state = getChannelState(channelUuid);
  const inFlight = inFlightNewerByChannel.get(channelUuid);
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
        error: error instanceof Error ? error.message : 'Failed to load newer messages.',
      });
    } finally {
      inFlightNewerByChannel.delete(channelUuid);
    }
  })();

  inFlightNewerByChannel.set(channelUuid, task);
  return task;
}

export async function syncChannelFromLatestCursor(channelUuid: string): Promise<void> {
  const inFlight = inFlightNewerByChannel.get(channelUuid);
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
        error: error instanceof Error ? error.message : 'Failed to synchronize messages.',
      });
    } finally {
      inFlightNewerByChannel.delete(channelUuid);
    }
  })();

  inFlightNewerByChannel.set(channelUuid, task);
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

function setLastReadMessageUuid(channelUuid: string, lastReadMessageUuid: string | null): void {
  lastReadMessageUuidByChannel.update((current) => ({
    ...current,
    [channelUuid]: lastReadMessageUuid,
  }));
}

export async function fetchChannelReadState(channelUuid: string): Promise<void> {
  let payload;
  try {
    payload = await fetchChannelReadStatePayload(channelUuid);
  } catch {
    return;
  }

  if (!payload) {
    return;
  }

  const unread = Number(payload.unreadCount ?? payload.unread_count ?? 0);
  const lastReadMessageUuid = payload.lastReadMessageUuid ?? payload.last_read_message_uuid ?? null;
  setUnreadCount(channelUuid, unread);
  setLastReadMessageUuid(channelUuid, lastReadMessageUuid);
}

export async function markChannelAsRead(
  channelUuid: string,
  lastReadMessageUuid?: string,
): Promise<void> {
  let payload;
  try {
    payload = await postChannelReadState(channelUuid, lastReadMessageUuid);
  } catch {
    return;
  }

  if (!payload) {
    return;
  }

  setUnreadCount(channelUuid, 0);
  setLastReadMessageUuid(
    channelUuid,
    payload.lastReadMessageUuid ?? payload.last_read_message_uuid ?? lastReadMessageUuid ?? null,
  );
}

export function addMessage(message: Message): void {
  if (message.is_deleted) {
    return;
  }

  const currentMessages = get(messagesByChannel)[message.channel_uuid] ?? [];
  if (currentMessages.some((item) => item.uuid === message.uuid)) {
    return;
  }

  const mergedBase = [...currentMessages];
  if (message.client_id) {
    markClientIdDelivered(message.channel_uuid, message.client_id);
    const pendingIndex = mergedBase.findIndex(
      (item) => item.pending && item.client_id === message.client_id,
    );

    if (pendingIndex >= 0) {
      mergedBase[pendingIndex] = {
        ...message,
        pending: false,
        failed: false,
      };
    } else {
      mergedBase.push(message);
    }
  } else {
    mergedBase.push(message);
  }

  const merged = dedupeByUuid(mergedBase);
  const windowed = applyWindowLimit(merged, 'newer');

  messagesByChannel.update((current) => ({
    ...current,
    [message.channel_uuid]: windowed.windowed,
  }));

  resolveMessageStateAfterAppend(message.channel_uuid, windowed.windowed);
}

export function updateMessage(message: Message): void {
  const currentMessages = get(messagesByChannel)[message.channel_uuid] ?? [];
  const index = currentMessages.findIndex((item) => item.uuid === message.uuid);
  if (index < 0) {
    return;
  }

  if (message.is_deleted) {
    const withoutDeleted = currentMessages.filter((item) => item.uuid !== message.uuid);
    messagesByChannel.update((current) => ({
      ...current,
      [message.channel_uuid]: withoutDeleted,
    }));
    return;
  }

  const updatedMessages = [...currentMessages];
  updatedMessages[index] = {
    ...updatedMessages[index],
    ...message,
    pending: false,
    failed: false,
  };

  messagesByChannel.update((current) => ({
    ...current,
    [message.channel_uuid]: updatedMessages,
  }));
}

export function softDeleteMessage(message: Message): void {
  const currentMessages = get(messagesByChannel)[message.channel_uuid] ?? [];
  const withoutDeleted = currentMessages.filter((item) => item.uuid !== message.uuid);
  messagesByChannel.update((current) => ({
    ...current,
    [message.channel_uuid]: withoutDeleted,
  }));
}

function getRandomClientId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createClientMessageId(): string {
  return getRandomClientId();
}

export function addPendingMessage(channelUuid: string, content: string, clientId: string): void {
  if (wasClientIdDelivered(channelUuid, clientId)) {
    return;
  }

  const currentMessages = get(messagesByChannel)[channelUuid] ?? [];
  if (currentMessages.some((message) => message.client_id === clientId)) {
    return;
  }

  const pendingMessage: Message = {
    uuid: `pending-${clientId}`,
    channel_uuid: channelUuid,
    content,
    author: 'Ty',
    created_at: new Date().toISOString(),
    client_id: clientId,
    pending: true,
    failed: false,
    reactions: [],
  };

  const merged = dedupeByUuid([...currentMessages, pendingMessage]);
  const windowed = applyWindowLimit(merged, 'newer');

  messagesByChannel.update((current) => ({
    ...current,
    [channelUuid]: windowed.windowed,
  }));

  resolveMessageStateAfterAppend(channelUuid, windowed.windowed);
}

export function markPendingMessageFailed(channelUuid: string, clientId: string): void {
  const currentMessages = get(messagesByChannel)[channelUuid] ?? [];
  const failedMessages = currentMessages.map((message) => {
    if (message.pending && message.client_id === clientId) {
      return {
        ...message,
        failed: true,
      };
    }

    return message;
  });

  messagesByChannel.update((current) => ({
    ...current,
    [channelUuid]: failedMessages,
  }));
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
    ...defaultChannelQueryState,
  });

  unreadCountByChannel.update((current) => ({
    ...current,
    [channelUuid]: 0,
  }));
  setLastReadMessageUuid(channelUuid, null);
}

export function resetChatState(): void {
  messagesByChannel.set({});
  channelQueryStateById.set({});
  unreadCountByChannel.set({});
  lastReadMessageUuidByChannel.set({});

  inFlightInitialByChannel.clear();
  inFlightOlderByChannel.clear();
  inFlightNewerByChannel.clear();
  requestIdCounterByChannel.clear();
  deliveredClientIdsByChannel.clear();
}
