import type { Message, MessageReadDto } from '../../../types/gateway';

export type MessagesByChannel = Record<string, Message[]>;

export type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error';

export type ChannelQueryState = {
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

export type NormalizedPaginatedPayload = {
  items: MessageReadDto[];
  hasMoreOlder: boolean;
  hasMoreNewer: boolean;
  nextBefore: string | null;
  nextAfter: string | null;
};

export type FetchDirection = 'initial' | 'older' | 'newer';

export type ReadStatePayload = {
  unreadCount?: number;
  unread_count?: number;
  lastReadMessageUuid?: string | null;
  last_read_message_uuid?: string | null;
};

export const defaultChannelQueryState: ChannelQueryState = {
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
