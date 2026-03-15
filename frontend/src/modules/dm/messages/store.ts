import { get, writable } from 'svelte/store';
import { activeDMConversation } from '../../../lib/stores/ui';
import type { DMConversation, DMMessage } from '../../../types/gateway';
import {
  createDMConversationRequest,
  fetchDMConversations,
  fetchDMMessagesPage,
  openDirectConversationRequest,
  postDMConversationReadState,
  postDMMessage,
} from './api';
import { defaultDMQueryState, type DMQueryState } from './types';
import {
  dedupeDMMessages,
  isDMCacheFresh,
  mapConversation,
  mapDMMessage,
  mergeDMMessages,
  sortConversations,
} from './utils';

export const dmConversations = writable<DMConversation[]>([]);
export const dmMessagesByConversation = writable<Record<string, DMMessage[]>>({});
export const dmQueryStateByConversation = writable<Record<string, DMQueryState>>({});

const inFlightInitial = new Map<string, Promise<void>>();
const inFlightOlder = new Map<string, Promise<void>>();
const inFlightNewer = new Map<string, Promise<void>>();
let inFlightConversations: Promise<void> | null = null;

function patchQueryState(conversationUuid: string, patch: Partial<DMQueryState>): void {
  dmQueryStateByConversation.update((current) => ({
    ...current,
    [conversationUuid]: {
      ...(current[conversationUuid] ?? defaultDMQueryState),
      ...patch,
    },
  }));
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

function isFresh(conversationUuid: string): boolean {
  const state = get(dmQueryStateByConversation)[conversationUuid] ?? defaultDMQueryState;
  const hasData = conversationUuid in get(dmMessagesByConversation);
  return isDMCacheFresh(hasData, state.fetchedAt);
}

async function runFetch(
  conversationUuid: string,
  direction: 'initial' | 'older' | 'newer',
): Promise<void> {
  const state = get(dmQueryStateByConversation)[conversationUuid] ?? defaultDMQueryState;
  const payload = await fetchDMMessagesPage(conversationUuid, {
    before: direction === 'older' ? state.nextBefore : null,
    after: direction === 'newer' ? state.nextAfter : null,
  });

  const mapped = (payload.items ?? []).map((item) => mapDMMessage(conversationUuid, item));

  dmMessagesByConversation.update((current) => {
    const existing = current[conversationUuid] ?? [];
    return {
      ...current,
      [conversationUuid]: mergeDMMessages(existing, mapped, direction),
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

export async function ensureDMConversations(force = false): Promise<void> {
  if (inFlightConversations && !force) {
    return inFlightConversations;
  }

  const run = (async () => {
    const data = await fetchDMConversations();
    dmConversations.set(sortConversations(data.map(mapConversation)));
  })();

  inFlightConversations = run;
  try {
    await run;
  } finally {
    inFlightConversations = null;
  }
}

export async function ensureDMMessages(conversationUuid: string): Promise<void> {
  if (isFresh(conversationUuid)) {
    return;
  }

  const inFlight = inFlightInitial.get(conversationUuid);
  if (inFlight) {
    return inFlight;
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
      inFlightInitial.delete(conversationUuid);
    });

  inFlightInitial.set(conversationUuid, run);
  return run;
}

export async function loadOlderDMMessages(conversationUuid: string): Promise<void> {
  const state = get(dmQueryStateByConversation)[conversationUuid] ?? defaultDMQueryState;
  const inFlight = inFlightOlder.get(conversationUuid);
  if (inFlight || !state.hasMoreOlder || !state.nextBefore) {
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
      inFlightOlder.delete(conversationUuid);
    });

  inFlightOlder.set(conversationUuid, run);
  return run;
}

export async function loadNewerDMMessages(conversationUuid: string): Promise<void> {
  const state = get(dmQueryStateByConversation)[conversationUuid] ?? defaultDMQueryState;
  const inFlight = inFlightNewer.get(conversationUuid);
  if (inFlight || !state.hasMoreNewer || !state.nextAfter) {
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
      inFlightNewer.delete(conversationUuid);
    });

  inFlightNewer.set(conversationUuid, run);
  return run;
}

export function addDMMessage(message: DMMessage): void {
  dmMessagesByConversation.update((current) => {
    const existing = current[message.conversation_uuid] ?? [];
    return {
      ...current,
      [message.conversation_uuid]: dedupeDMMessages([...existing, message]),
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
      [message.conversation_uuid]: existing.map((item) =>
        item.uuid === message.uuid ? { ...item, ...message } : item,
      ),
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
  const dto = await postDMMessage(conversationUuid, content);
  const mapped = mapDMMessage(conversationUuid, dto);
  addDMMessage(mapped);
  return mapped;
}

export async function markDMConversationAsRead(
  conversationUuid: string,
  lastReadMessageUuid?: string,
): Promise<void> {
  await postDMConversationReadState(conversationUuid, lastReadMessageUuid);
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

  const dto = await createDMConversationRequest(normalizedParticipants, title);
  const mapped = mapConversation(dto);
  upsertConversation(mapped);
  return mapped;
}

export async function openDirectConversation(userUuid: string): Promise<DMConversation> {
  const dto = await openDirectConversationRequest(userUuid);
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

  inFlightInitial.clear();
  inFlightOlder.clear();
  inFlightNewer.clear();
  inFlightConversations = null;
}
