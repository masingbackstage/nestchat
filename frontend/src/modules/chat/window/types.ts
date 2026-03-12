import type { Channel, Message, Server } from '../../../types/gateway';

export type WindowReactionEmoji = {
  token: string;
  label: string;
  imageUrl: string | null;
};

export type WindowViewModel = {
  currentMessages: Message[];
  currentChannelQuery: WindowChannelQueryState | null;
  currentUnreadCount: number;
  currentLastReadMessageUuid: string | null;
  firstNewMessageIndex: number;
  isInitialLoading: boolean;
  customReactionEmojis: WindowReactionEmoji[];
};

export type UnreadMarkerMessage = Pick<Message, 'uuid'>;

export type WindowChannelQueryState = {
  isLoadingInitial: boolean;
  isLoadingOlder: boolean;
  isLoadingNewer: boolean;
  hasMoreOlder: boolean;
  hasMoreNewer: boolean;
  nextBefore: string | null;
  nextAfter: string | null;
  error: string | null;
};

export type ViewportState = {
  loadingOlderFromScroll: boolean;
  loadingNewerFromScroll: boolean;
  lastAutoScrolledChannelUuid: string | null;
  previousChannelUuid: string | null;
  previousMessageCount: number;
  isViewportNearBottom: boolean;
  forceScrollToBottom: boolean;
  isPositioningAfterViewSwitch: boolean;
};

export type MessageActionState = {
  busyMessageActions: Set<string>;
  pendingDeleteMessageUuid: string | null;
  isDeleteConfirmSubmitting: boolean;
};

export type ManageableMessage = Pick<Message, 'author_uuid' | 'pending' | 'is_deleted'>;

export type MessageEventDetail = {
  messageUuid: string;
};

export type EditMessageEventDetail = MessageEventDetail & {
  content: string;
};

export type ReactionEventDetail = MessageEventDetail & {
  emoji: string;
};

export type ActiveWindowContext = {
  activeChannel: Channel | null;
  activeServer: Server | null;
};
