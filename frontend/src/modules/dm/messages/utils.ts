import { toApiAbsoluteUrl } from '../../../lib/url';
import type {
  DMConversation,
  DMMessage,
  DMMessageReadDto,
  PaginatedDMMessagesResponse,
} from '../../../types/gateway';

export const DM_PAGE_LIMIT = 50;
export const DM_CACHE_TTL_MS = 60_000;

export function mapDMMessage(conversationUuid: string, item: DMMessageReadDto): DMMessage {
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

export function mapConversation(item: DMConversation): DMConversation {
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

export function sortConversations(conversations: DMConversation[]): DMConversation[] {
  return [...conversations].sort(
    (a, b) =>
      new Date(b.updatedAt ?? b.updated_at ?? 0).getTime() -
      new Date(a.updatedAt ?? a.updated_at ?? 0).getTime(),
  );
}

export function normalizeMessagesPayload(raw: unknown): PaginatedDMMessagesResponse {
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

export function dedupeDMMessages(messages: DMMessage[]): DMMessage[] {
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

export function mergeDMMessages(
  existing: DMMessage[],
  incoming: DMMessage[],
  direction: 'initial' | 'older' | 'newer',
): DMMessage[] {
  if (direction === 'initial') {
    return dedupeDMMessages(incoming);
  }

  const merged = direction === 'older' ? [...incoming, ...existing] : [...existing, ...incoming];
  return dedupeDMMessages(merged);
}

export function isDMCacheFresh(hasData: boolean, fetchedAt: number | null): boolean {
  if (!hasData || !fetchedAt) {
    return false;
  }

  return Date.now() - fetchedAt <= DM_CACHE_TTL_MS;
}
