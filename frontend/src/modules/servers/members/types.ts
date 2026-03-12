import type { MemberRole } from '../../../types/gateway';

export type MemberItem = {
  uuid: string;
  displayName: string;
  isOnline: boolean;
  roles: MemberRole[];
  avatarUrl: string | null;
  customStatus: string | null;
};

export type MembersGroup = {
  key: string;
  label: string;
  members: MemberItem[];
};

export type MembersQueryState = {
  fetchedAt: number | null;
  isLoading: boolean;
  error: string | null;
};
