import type { Channel, Message, ServerEmoji } from '../../../types/gateway';
import { getFirstNewMessageIndex, mapCustomReactionEmojis } from './utils';
import type { WindowChannelQueryState, WindowViewModel } from './types';

type BuildWindowViewModelArgs = {
  activeChannel: Channel | null;
  messagesByChannel: Record<string, Message[]>;
  channelQueryStateById: Record<string, WindowChannelQueryState>;
  unreadCountByChannel: Record<string, number>;
  lastReadMessageUuidByChannel: Record<string, string | null>;
  currentServerEmojis: ServerEmoji[];
};

export function getCurrentServerEmojis(
  activeServerUuid: string | null,
  serverEmojisByServer: Record<string, ServerEmoji[]>,
): ServerEmoji[] {
  if (!activeServerUuid) {
    return [];
  }

  return serverEmojisByServer[activeServerUuid] ?? [];
}

export function buildWindowViewModel({
  activeChannel,
  messagesByChannel,
  channelQueryStateById,
  unreadCountByChannel,
  lastReadMessageUuidByChannel,
  currentServerEmojis,
}: BuildWindowViewModelArgs): WindowViewModel {
  const activeChannelUuid = activeChannel?.uuid ?? null;
  const currentMessages = activeChannelUuid ? (messagesByChannel[activeChannelUuid] ?? []) : [];
  const currentChannelQuery = activeChannelUuid ? (channelQueryStateById[activeChannelUuid] ?? null) : null;
  const currentUnreadCount = activeChannelUuid ? (unreadCountByChannel[activeChannelUuid] ?? 0) : 0;
  const currentLastReadMessageUuid = activeChannelUuid
    ? (lastReadMessageUuidByChannel[activeChannelUuid] ?? null)
    : null;

  return {
    currentMessages,
    currentChannelQuery,
    currentUnreadCount,
    currentLastReadMessageUuid,
    firstNewMessageIndex: getFirstNewMessageIndex(
      currentMessages,
      currentUnreadCount,
      currentLastReadMessageUuid,
    ),
    isInitialLoading: Boolean(
      activeChannel && currentMessages.length === 0 && currentChannelQuery?.isLoadingInitial,
    ),
    customReactionEmojis: mapCustomReactionEmojis(currentServerEmojis),
  };
}
