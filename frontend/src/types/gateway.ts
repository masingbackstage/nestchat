export type Channel = {
  uuid: string;
  name: string;
  channelEmoji?: string | null;
  channel_emoji?: string | null;
  channelType?: string;
  channel_type?: string;
  topic?: string | null;
  isPublic?: boolean;
  is_public?: boolean;
  voiceOccupants?: VoiceOccupant[];
  voice_occupants?: VoiceOccupant[];
};

export type VoiceOccupant = {
  userUuid?: string;
  user_uuid?: string;
  displayName?: string;
  display_name?: string;
  avatarUrl?: string | null;
  avatar_url?: string | null;
  isMuted?: boolean;
  is_muted?: boolean;
  isSpeaking?: boolean;
  is_speaking?: boolean;
  audioLevel?: number;
  audio_level?: number;
  isCameraOn?: boolean;
  is_camera_on?: boolean;
  isScreenSharing?: boolean;
  is_screen_sharing?: boolean;
};

export type Server = {
  uuid: string;
  name: string;
  avatarUrl?: string | null;
  avatar_url?: string | null;
  isOwner?: boolean;
  is_owner?: boolean;
  channels: Channel[];
};

export type CreateChannelRequest = {
  name: string;
  channel_emoji?: string;
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

export type ServerEmoji = {
  uuid: string;
  name: string;
  token?: string;
  imageUrl?: string | null;
  image_url?: string | null;
  isAnimated?: boolean;
  is_animated?: boolean;
};

export type ServerMemberItem = {
  uuid: string;
  displayName?: string;
  display_name?: string;
  isOnline?: boolean;
  is_online?: boolean;
  roles?: MemberRole[];
  avatarUrl?: string | null;
  avatar_url?: string | null;
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

export type VoiceMembersChangedPayload = {
  serverUuid?: string;
  server_uuid?: string;
  channelUuid?: string;
  channel_uuid?: string;
  occupants?: VoiceOccupant[];
  timestamp?: string;
};

export type Message = {
  uuid: string;
  channel_uuid: string;
  content: string;
  author: string;
  avatar_url?: string | null;
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
  avatarUrl?: string | null;
  avatar_url?: string | null;
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

export type DMParticipant = {
  uuid: string;
  displayName?: string;
  display_name?: string;
  avatarUrl?: string | null;
  avatar_url?: string | null;
  isOnline?: boolean;
  is_online?: boolean;
};

export type DMConversation = {
  uuid: string;
  conversationType?: 'DIRECT' | 'GROUP';
  conversation_type?: 'DIRECT' | 'GROUP';
  title?: string | null;
  avatarUrl?: string | null;
  avatar_url?: string | null;
  participants?: DMParticipant[];
  lastMessage?: DMMessage | null;
  last_message?: DMMessage | null;
  unreadCount?: number;
  unread_count?: number;
  createdAt?: string;
  created_at?: string;
  updatedAt?: string;
  updated_at?: string;
};

export type DMMessage = {
  uuid: string;
  conversation_uuid: string;
  channel_uuid: string;
  content: string;
  author: string;
  avatar_url?: string | null;
  author_uuid?: string;
  created_at?: string;
  updated_at?: string;
  is_deleted?: boolean;
  is_edited?: boolean;
  edited_at?: string | null;
  reactions?: MessageReaction[];
  ciphertext?: string | null;
  nonce?: string | null;
  encryption_version?: string | null;
  sender_key_id?: string | null;
  client_id?: string;
  pending?: boolean;
  failed?: boolean;
};

export type DMMessageReadDto = {
  uuid: string;
  conversationUuid?: string;
  conversation_uuid?: string;
  author: string | number;
  authorProfileDisplayName?: string | null;
  author_profile_display_name?: string | null;
  avatarUrl?: string | null;
  avatar_url?: string | null;
  content: string;
  isDeleted?: boolean;
  is_deleted?: boolean;
  isEdited?: boolean;
  is_edited?: boolean;
  editedAt?: string | null;
  edited_at?: string | null;
  reactions?: MessageReaction[];
  ciphertext?: string | null;
  nonce?: string | null;
  encryptionVersion?: string | null;
  encryption_version?: string | null;
  senderKeyId?: string | null;
  sender_key_id?: string | null;
  createdAt?: string;
  created_at?: string;
  updatedAt?: string;
  updated_at?: string;
};

export type PaginatedDMMessagesResponse = {
  items: DMMessageReadDto[];
  hasMoreOlder?: boolean;
  has_more_older?: boolean;
  hasMoreNewer?: boolean;
  has_more_newer?: boolean;
  nextBefore?: string | null;
  next_before?: string | null;
  nextAfter?: string | null;
  next_after?: string | null;
};

export type FriendUser = {
  uuid: string;
  relationUuid?: string;
  relation_uuid?: string;
  email: string;
  displayName?: string;
  display_name?: string;
  tag?: string;
  avatarUrl?: string | null;
  avatar_url?: string | null;
  isOnline?: boolean;
  is_online?: boolean;
  customStatus?: string;
  custom_status?: string;
};

export type FriendRequest = {
  uuid: string;
  status: 'PENDING' | 'ACCEPTED' | 'DECLINED' | 'CANCELED';
  createdAt?: string;
  created_at?: string;
  updatedAt?: string;
  updated_at?: string;
  respondedAt?: string | null;
  responded_at?: string | null;
  user: FriendUser;
};

export type UserSearchResult = FriendUser;
