export type Channel = {
  uuid: string;
  name: string;
  channel_type: string;
};

export type Server = {
  uuid: string;
  name: string;
  channels: Channel[];
};

export type Message = {
  uuid: string;
  channel_uuid: string;
  content: string;
  author: string;
  created_at?: string;
};

export type MessageReadDto = {
  uuid: string;
  author: string | number;
  authorProfileDisplayName?: string | null;
  author_profile_display_name?: string | null;
  content: string;
  createdAt?: string;
  created_at?: string;
};

export type PaginatedMessagesResponse = {
  items: MessageReadDto[];
  hasMoreOlder?: boolean;
  has_more_older?: boolean;
  hasMoreNewer?: boolean;
  has_more_newer?: boolean;
  nextBefore?: string | null;
  next_before?: string | null;
  nextAfter?: string | null;
  next_after?: string | null;
};

export type GatewayMessageEvent = {
  module: string;
  action: string;
  payload: unknown;
};
