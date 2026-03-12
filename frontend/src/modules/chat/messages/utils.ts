import { toApiAbsoluteUrl } from '../../../lib/url';
import type { Message, MessageReadDto, PaginatedMessagesResponse } from '../../../types/gateway';
import type { ChannelQueryState, FetchDirection, NormalizedPaginatedPayload } from './types';

export const PAGE_LIMIT = 50;
export const CHANNEL_MESSAGES_CACHE_TTL_MS = 60_000;
export const MAX_MESSAGES_PER_CHANNEL = 300;

export function mapApiMessages(channelUuid: string, items: MessageReadDto[]): Message[] {
  return items
    .map((item) => ({
      uuid: item.uuid,
      channel_uuid: item.channelUuid ?? item.channel_uuid ?? channelUuid,
      content: item.content,
      author:
        item.authorProfileDisplayName ?? item.author_profile_display_name ?? String(item.author),
      avatar_url: toApiAbsoluteUrl(item.avatarUrl ?? item.avatar_url ?? null),
      author_uuid: String(item.author),
      is_deleted: Boolean(item.isDeleted ?? item.is_deleted ?? false),
      is_edited: Boolean(item.isEdited ?? item.is_edited ?? false),
      edited_at: item.editedAt ?? item.edited_at ?? null,
      reactions: (item.reactions ?? []).map((reaction) => ({
        emoji: reaction.emoji,
        count: Number(reaction.count ?? 0),
        reacted_by_me: Boolean(reaction.reactedByMe ?? reaction.reacted_by_me ?? false),
      })),
      created_at: item.createdAt ?? item.created_at,
      updated_at: item.updatedAt ?? item.updated_at,
    }))
    .filter((message) => !message.is_deleted);
}

export function normalizePaginatedPayload(raw: unknown): NormalizedPaginatedPayload {
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

export function dedupeByUuid(messages: Message[]): Message[] {
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

export function getEdgeMessage(messages: Message[], edge: 'oldest' | 'newest'): Message | null {
  if (messages.length === 0) {
    return null;
  }

  const message = edge === 'oldest' ? messages[0] : messages[messages.length - 1];
  return message ?? null;
}

export function buildCursorFromMessage(message: Message | null): string | null {
  if (!message?.created_at) {
    return null;
  }

  return `${message.created_at}|${message.uuid}`;
}

export function applyWindowLimit(
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

export function mergeMessagesByDirection(
  existing: Message[],
  incoming: Message[],
  direction: FetchDirection,
): {
  merged: Message[];
  trimmedOlder: boolean;
  trimmedNewer: boolean;
} {
  if (direction === 'initial') {
    return {
      merged: dedupeByUuid(incoming),
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

export function isChannelCacheFresh(hasCache: boolean, state: ChannelQueryState): boolean {
  if (!hasCache || !state.fetchedAt) {
    return false;
  }

  return Date.now() - state.fetchedAt <= CHANNEL_MESSAGES_CACHE_TTL_MS;
}
