import { authFetch } from '../../lib/auth';
import type { Channel, CreateChannelRequest } from '../../types/gateway';

function pick<T>(
  payload: Record<string, unknown>,
  camelKey: string,
  snakeKey: string,
): T | undefined {
  return (payload[camelKey] as T | undefined) ?? (payload[snakeKey] as T | undefined);
}

function mapChannelResponse(payload: unknown): Channel {
  const raw = payload as Record<string, unknown>;
  return {
    uuid: String(raw.uuid ?? ''),
    name: String(raw.name ?? ''),
    channel_type: pick<string>(raw, 'channelType', 'channel_type'),
    topic: pick<string | null>(raw, 'topic', 'topic') ?? null,
    is_public: pick<boolean>(raw, 'isPublic', 'is_public') ?? true,
  };
}

export async function createChannel(
  serverUuid: string,
  data: CreateChannelRequest,
): Promise<Channel> {
  const baseUrl = import.meta.env.VITE_API_URL;
  if (!baseUrl) {
    throw new Error('Missing VITE_API_URL.');
  }

  const response = await authFetch(`${baseUrl}/servers/${serverUuid}/channels/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status} ${text}`);
  }

  const payload = (await response.json()) as unknown;
  return mapChannelResponse(payload);
}
