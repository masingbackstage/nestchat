import { authFetch } from '../../../lib/auth';
import { getApiBaseUrl } from '../../../lib/url';
import type { NormalizedPaginatedPayload, ReadStatePayload } from './types';
import { normalizePaginatedPayload, PAGE_LIMIT } from './utils';

export async function fetchMessagesPage(
  channelUuid: string,
  options: {
    before?: string | null;
    after?: string | null;
  },
): Promise<NormalizedPaginatedPayload> {
  const params = new URLSearchParams({
    channel_uuid: channelUuid,
    limit: String(PAGE_LIMIT),
  });

  if (options.before) {
    params.set('before', options.before);
  }
  if (options.after) {
    params.set('after', options.after);
  }

  const response = await authFetch(`${getApiBaseUrl()}/chat/messages/?${params.toString()}`);
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`HTTP ${response.status} ${errorBody}`);
  }

  const rawData = (await response.json()) as unknown;
  return normalizePaginatedPayload(rawData);
}

export async function fetchChannelReadStatePayload(
  channelUuid: string,
): Promise<ReadStatePayload | null> {
  const params = new URLSearchParams({ channel_uuid: channelUuid });
  const response = await authFetch(`${getApiBaseUrl()}/chat/read-state/?${params.toString()}`);

  if (!response.ok) {
    return null;
  }

  return (await response.json()) as ReadStatePayload;
}

export async function postChannelReadState(
  channelUuid: string,
  lastReadMessageUuid?: string,
): Promise<ReadStatePayload | null> {
  const body: Record<string, string> = { channel_uuid: channelUuid };
  if (lastReadMessageUuid) {
    body.last_read_message_uuid = lastReadMessageUuid;
  }

  const response = await authFetch(`${getApiBaseUrl()}/chat/read-state/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    return null;
  }

  return (await response.json()) as ReadStatePayload;
}
