import { authFetch } from '../../../lib/auth';
import { getApiBaseUrl } from '../../../lib/url';
import type {
  DMConversation,
  DMMessageReadDto,
  PaginatedDMMessagesResponse,
} from '../../../types/gateway';
import { normalizeMessagesPayload, DM_PAGE_LIMIT } from './utils';

export async function fetchDMConversations(): Promise<DMConversation[]> {
  const response = await authFetch(`${getApiBaseUrl()}/dm/conversations/`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return (await response.json()) as DMConversation[];
}

export async function fetchDMMessagesPage(
  conversationUuid: string,
  options: { before?: string | null; after?: string | null },
): Promise<PaginatedDMMessagesResponse> {
  const params = new URLSearchParams({
    limit: String(DM_PAGE_LIMIT),
  });

  if (options.before) {
    params.set('before', options.before);
  }
  if (options.after) {
    params.set('after', options.after);
  }

  const response = await authFetch(
    `${getApiBaseUrl()}/dm/conversations/${conversationUuid}/messages/?${params.toString()}`,
  );
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status} ${body}`);
  }

  return normalizeMessagesPayload(await response.json());
}

export async function createDMConversationRequest(
  participantUuids: string[],
  title?: string,
): Promise<DMConversation> {
  const response = await authFetch(`${getApiBaseUrl()}/dm/conversations/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      participant_uuids: participantUuids,
      ...(title?.trim() ? { title: title.trim() } : {}),
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status} ${body}`);
  }

  return (await response.json()) as DMConversation;
}

export async function openDirectConversationRequest(userUuid: string): Promise<DMConversation> {
  const response = await authFetch(`${getApiBaseUrl()}/dm/conversations/direct/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_uuid: userUuid }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status} ${body}`);
  }

  return (await response.json()) as DMConversation;
}

export async function postDMMessage(
  conversationUuid: string,
  content: string,
): Promise<DMMessageReadDto> {
  const response = await authFetch(`${getApiBaseUrl()}/dm/conversations/${conversationUuid}/messages/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status} ${body}`);
  }

  return (await response.json()) as DMMessageReadDto;
}

export async function postDMConversationReadState(
  conversationUuid: string,
  lastReadMessageUuid?: string,
): Promise<void> {
  await authFetch(`${getApiBaseUrl()}/dm/conversations/${conversationUuid}/read-state/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...(lastReadMessageUuid ? { last_read_message_uuid: lastReadMessageUuid } : {}),
    }),
  });
}
