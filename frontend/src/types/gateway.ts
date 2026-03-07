export type Channel = {
  uuid: string;
  name: string;
  channelType?: string;
  channel_type?: string;
  topic?: string | null;
  isPublic?: boolean;
  is_public?: boolean;
};

export type Server = {
  uuid: string;
  name: string;
  isOwner?: boolean;
  is_owner?: boolean;
  channels: Channel[];
};

export type CreateChannelRequest = {
  name: string;
  channel_type: 'TEXT' | 'VOICE';
  topic?: string;
  is_public: boolean;
  allowed_roles: string[];
};

export type MessageReaction = {
  emoji: string;
  count: number;
  reacted_by_me?: boolean;
  reactedByMe?: boolean;
};

export type MemberRole = {
  uuid: string;
  name: string;
};

export type ServerMemberItem = {
  uuid: string;
  displayName?: string;
  display_name?: string;
  isOnline?: boolean;
  is_online?: boolean;
  roles?: MemberRole[];
  avatar?: string | null;
  customStatus?: string | null;
  custom_status?: string | null;
};

export type ServerMembersGroup = {
  key: string;
  label: string;
  members: ServerMemberItem[];
};

export type ServerMembersResponse = {
  groups: ServerMembersGroup[];
};

export type PresenceStatusChangedPayload = {
  serverUuid?: string;
  server_uuid?: string;
  memberUuid?: string;
  member_uuid?: string;
  isOnline?: boolean;
  is_online?: boolean;
  timestamp?: string;
};

export type PresenceMembersChangedPayload = {
  serverUuid?: string;
  server_uuid?: string;
  reason?: string;
  timestamp?: string;
};

export type Message = {
  uuid: string;
  channel_uuid: string;
  content: string;
  author: string;
  author_uuid?: string;
  created_at?: string;
  updated_at?: string;
  is_deleted?: boolean;
  is_edited?: boolean;
  edited_at?: string | null;
  reactions?: MessageReaction[];
  client_id?: string;
  pending?: boolean;
  failed?: boolean;
};

export type MessageReadDto = {
  uuid: string;
  channelUuid?: string;
  channel_uuid?: string;
  author: string | number;
  authorProfileDisplayName?: string | null;
  author_profile_display_name?: string | null;
  content: string;
  isDeleted?: boolean;
  is_deleted?: boolean;
  isEdited?: boolean;
  is_edited?: boolean;
  editedAt?: string | null;
  edited_at?: string | null;
  reactions?: MessageReaction[];
  createdAt?: string;
  created_at?: string;
  updatedAt?: string;
  updated_at?: string;
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
