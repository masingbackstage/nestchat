import type {
  GatewayMessageEvent,
  Message,
  PresenceMembersChangedPayload,
  PresenceStatusChangedPayload,
} from '../types/gateway';
import type { DMMessage } from '../types/gateway';

export type GatewayEventHandlerDeps = {
  toApiAbsoluteUrl: (value: string | null | undefined) => string | null;
  pushToast: (input: { type: 'success' | 'error'; message: string }) => number;
  ensureServerMembers: (serverUuid: string, force?: boolean) => Promise<void>;
  updateServerMemberPresence: (
    serverUuid: string,
    memberUuid: string,
    isOnline: boolean,
  ) => boolean;
  addMessage: (message: Message) => void;
  incrementUnreadCount: (channelUuid: string) => void;
  softDeleteMessage: (message: Message) => void;
  updateMessage: (message: Message) => void;
  addDMMessage: (message: DMMessage) => void;
  updateDMMessage: (message: DMMessage) => void;
  softDeleteDMMessage: (message: DMMessage) => void;
  updateDMConversationPreview: (conversationUuid: string, message: DMMessage) => void;
  incrementDMUnread: (conversationUuid: string) => void;
  clearDMUnread: (conversationUuid: string) => void;
  getActiveChannelUuid: () => string | null;
  getActiveDMConversationUuid: () => string | null;
};

type ChatGatewayPayload = {
  uuid?: string;
  id?: string;
  channel_id?: string;
  channel_uuid?: string;
  channelUuid?: string;
  conversation_uuid?: string;
  conversationUuid?: string;
  content: string;
  author: string;
  author_uuid?: string;
  author_profile_display_name?: string;
  authorProfileDisplayName?: string;
  avatar_url?: string | null;
  avatarUrl?: string | null;
  is_deleted?: boolean;
  isDeleted?: boolean;
  is_edited?: boolean;
  isEdited?: boolean;
  edited_at?: string | null;
  editedAt?: string | null;
  reactions?: {
    emoji: string;
    count: number;
    reacted_by_me?: boolean;
    reactedByMe?: boolean;
  }[];
  updated_at?: string;
  updatedAt?: string;
  created_at?: string;
  createdAt?: string;
  client_id?: string;
  clientId?: string;
};

function mapReactions(payload: ChatGatewayPayload): {
  emoji: string;
  count: number;
  reacted_by_me: boolean;
}[] {
  return (payload.reactions ?? []).map((reaction) => ({
    emoji: reaction.emoji,
    count: Number(reaction.count ?? 0),
    reacted_by_me: Boolean(reaction.reactedByMe ?? reaction.reacted_by_me ?? false),
  }));
}

function mapChannelMessage(payload: ChatGatewayPayload, deps: GatewayEventHandlerDeps): Message {
  const channelUuid = payload.channel_id ?? payload.channel_uuid ?? payload.channelUuid ?? '';
  return {
    uuid: payload.id ?? payload.uuid ?? '',
    channel_uuid: channelUuid,
    content: payload.content ?? '',
    author:
      payload.authorProfileDisplayName ?? payload.author_profile_display_name ?? String(payload.author ?? ''),
    avatar_url: deps.toApiAbsoluteUrl(payload.avatarUrl ?? payload.avatar_url ?? null),
    author_uuid: payload.author_uuid ?? (payload.author ? String(payload.author) : undefined),
    is_deleted: Boolean(payload.isDeleted ?? payload.is_deleted ?? false),
    is_edited: Boolean(payload.isEdited ?? payload.is_edited ?? false),
    edited_at: payload.editedAt ?? payload.edited_at ?? null,
    reactions: mapReactions(payload),
    created_at: payload.createdAt ?? payload.created_at ?? new Date().toISOString(),
    updated_at: payload.updatedAt ?? payload.updated_at,
    client_id: payload.client_id ?? payload.clientId,
  };
}

function mapDMMessage(payload: ChatGatewayPayload, deps: GatewayEventHandlerDeps): DMMessage {
  const conversationUuid = payload.conversation_uuid ?? payload.conversationUuid ?? '';
  return {
    uuid: payload.uuid ?? payload.id ?? '',
    conversation_uuid: conversationUuid,
    channel_uuid: conversationUuid,
    content: payload.content ?? '',
    author:
      payload.authorProfileDisplayName ?? payload.author_profile_display_name ?? String(payload.author ?? ''),
    avatar_url: deps.toApiAbsoluteUrl(payload.avatarUrl ?? payload.avatar_url ?? null),
    author_uuid: payload.author ? String(payload.author) : undefined,
    is_deleted: Boolean(payload.isDeleted ?? payload.is_deleted ?? false),
    is_edited: Boolean(payload.isEdited ?? payload.is_edited ?? false),
    edited_at: payload.editedAt ?? payload.edited_at ?? null,
    reactions: mapReactions(payload),
    created_at: payload.createdAt ?? payload.created_at,
    updated_at: payload.updatedAt ?? payload.updated_at,
    ciphertext: null,
    nonce: null,
    encryption_version: null,
    sender_key_id: null,
    client_id: payload.client_id ?? payload.clientId,
  };
}

export function createGatewayEventHandler(deps: GatewayEventHandlerDeps) {
  return function handleGatewayEvent(event: GatewayMessageEvent): void {
    const moduleName = String(event.module ?? '').toLowerCase();
    const actionName = String(event.action ?? '').toLowerCase();

    if (moduleName === 'system' && actionName === 'error') {
      const payload = event.payload as { code?: string; detail?: string };
      if (payload.code === 'permission_denied' || payload.code === 'not_found') {
        deps.pushToast({
          type: 'error',
          message: payload.detail ?? 'Channel permission error.',
        });
      }
      return;
    }

    if (moduleName === 'presence' && actionName === 'status_changed') {
      const payload = event.payload as PresenceStatusChangedPayload;
      const serverUuid = payload.serverUuid ?? payload.server_uuid;
      const memberUuid = payload.memberUuid ?? payload.member_uuid;
      if (!serverUuid || !memberUuid) {
        return;
      }

      const knownMember = deps.updateServerMemberPresence(
        serverUuid,
        memberUuid,
        Boolean(payload.isOnline ?? payload.is_online ?? false),
      );
      if (!knownMember) {
        void deps.ensureServerMembers(serverUuid, true);
      }
      return;
    }

    if (moduleName === 'presence' && actionName === 'members_changed') {
      const payload = event.payload as PresenceMembersChangedPayload;
      const serverUuid = payload.serverUuid ?? payload.server_uuid;
      if (!serverUuid) {
        return;
      }
      void deps.ensureServerMembers(serverUuid, true);
      return;
    }

    if (moduleName !== 'chat') {
      return;
    }

    const payload = event.payload as ChatGatewayPayload;
    const channelUuid = payload.channel_id ?? payload.channel_uuid ?? payload.channelUuid;
    const dmConversationUuid = payload.conversation_uuid ?? payload.conversationUuid;

    if (actionName === 'new_message') {
      if (!channelUuid) {
        return;
      }

      const message = mapChannelMessage(payload, deps);
      deps.addMessage(message);
      if (deps.getActiveChannelUuid() !== channelUuid) {
        deps.incrementUnreadCount(channelUuid);
      }
      return;
    }

    if (
      (actionName === 'dm_new_message' ||
        actionName === 'dm_message_updated' ||
        actionName === 'dm_message_deleted' ||
        actionName === 'dm_message_reactions_updated') &&
      dmConversationUuid
    ) {
      const message = mapDMMessage(payload, deps);

      if (actionName === 'dm_new_message') {
        deps.addDMMessage(message);
        deps.updateDMConversationPreview(dmConversationUuid, message);
        if (deps.getActiveDMConversationUuid() !== dmConversationUuid) {
          deps.incrementDMUnread(dmConversationUuid);
        } else {
          deps.clearDMUnread(dmConversationUuid);
        }
      } else if (actionName === 'dm_message_deleted') {
        deps.softDeleteDMMessage(message);
        deps.updateDMConversationPreview(dmConversationUuid, message);
      } else {
        deps.updateDMMessage(message);
        deps.updateDMConversationPreview(dmConversationUuid, message);
      }
      return;
    }

    if (
      (actionName === 'message_updated' ||
        actionName === 'message_deleted' ||
        actionName === 'message_reactions_updated') &&
      channelUuid
    ) {
      const message = mapChannelMessage(payload, deps);

      if (actionName === 'message_deleted') {
        deps.softDeleteMessage(message);
      } else {
        deps.updateMessage(message);
      }
    }
  };
}
