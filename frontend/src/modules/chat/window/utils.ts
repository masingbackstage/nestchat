import type { ServerEmoji } from '../../../types/gateway';
import type { UnreadMarkerMessage, WindowReactionEmoji } from './types';

const NEAR_BOTTOM_THRESHOLD_PX = 80;

export function mapCustomReactionEmojis(serverEmojis: ServerEmoji[]): WindowReactionEmoji[] {
  return serverEmojis.map((emoji) => ({
    token: emoji.token ?? `:${emoji.name}:`,
    label: emoji.name,
    imageUrl: emoji.imageUrl ?? emoji.image_url ?? null,
  }));
}

export function getFirstNewMessageIndex(
  messages: UnreadMarkerMessage[],
  unreadCount: number,
  lastReadMessageUuid: string | null,
): number {
  if (messages.length === 0 || unreadCount <= 0) {
    return -1;
  }

  if (lastReadMessageUuid) {
    const idx = messages.findIndex((message) => message.uuid === lastReadMessageUuid);
    if (idx >= 0) {
      return Math.min(messages.length, idx + 1);
    }
  }

  return Math.max(0, messages.length - unreadCount);
}

export function isNearBottom(container: HTMLDivElement): boolean {
  const distanceFromBottom = container.scrollHeight - (container.scrollTop + container.clientHeight);
  return distanceFromBottom <= NEAR_BOTTOM_THRESHOLD_PX;
}
