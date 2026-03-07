import { get, writable } from 'svelte/store';
import type { Message } from '../../types/gateway';

type MessagesByChannel = Record<string, Message[]>;

type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error';
type ChannelQueryState = {
  fetchedAt: number | null;
  isLoading: boolean;
  error: string | null;
  inFlightRequestId: number | null;
};

type MessageApiItem = {
  uuid: string;
  author: string | number;
  author_profile_display_name?: string | null;
  authorProfileDisplayName?: string | null;
  content: string;
  created_at?: string;
  createdAt?: string;
};

const CHANNEL_MESSAGES_CACHE_TTL_MS = 60_000;
const defaultQueryState: ChannelQueryState = {
  fetchedAt: null,
  isLoading: false,
  error: null,
  inFlightRequestId: null,
};

export const messagesByChannel = writable<MessagesByChannel>({});
export const chatConnectionStatus = writable<ConnectionStatus>('idle');
export const channelQueryStateById = writable<Record<string, ChannelQueryState>>({});

const inFlightByChannel: Record<string, Promise<void> | undefined> = {};
const requestIdCounterByChannel: Record<string, number> = {};

function getToken(): string | null {
  return import.meta.env.VITE_API_TOKEN ?? localStorage.getItem('access_token');
}

function getChannelState(channelUuid: string): ChannelQueryState {
  return get(channelQueryStateById)[channelUuid] ?? defaultQueryState;
}

function patchChannelState(channelUuid: string, patch: Partial<ChannelQueryState>): void {
  channelQueryStateById.update((current) => ({
    ...current,
    [channelUuid]: {
      ...(current[channelUuid] ?? defaultQueryState),
      ...patch,
    },
  }));
}

function mapApiMessages(channelUuid: string, rawData: unknown): Message[] {
  const items = Array.isArray(rawData)
    ? (rawData as MessageApiItem[])
    : ((rawData as { results?: MessageApiItem[] })?.results ?? []);

  return items.map((item) => ({
    uuid: item.uuid,
    channel_uuid: channelUuid,
    content: item.content,
    author:
      item.authorProfileDisplayName ?? item.author_profile_display_name ?? String(item.author),
    created_at: item.createdAt ?? item.created_at,
  }));
}

function isCacheFresh(channelUuid: string): boolean {
  const state = getChannelState(channelUuid);
  const hasCache = channelUuid in get(messagesByChannel);
  if (!hasCache || !state.fetchedAt) {
    return false;
  }

  return Date.now() - state.fetchedAt <= CHANNEL_MESSAGES_CACHE_TTL_MS;
}

async function fetchChannelMessages(channelUuid: string): Promise<void> {
  if (inFlightByChannel[channelUuid]) {
    return inFlightByChannel[channelUuid];
  }

  requestIdCounterByChannel[channelUuid] = (requestIdCounterByChannel[channelUuid] ?? 0) + 1;
  const requestId = requestIdCounterByChannel[channelUuid];
  patchChannelState(channelUuid, {
    isLoading: true,
    error: null,
    inFlightRequestId: requestId,
  });

  const task = (async () => {
    const baseUrl = import.meta.env.VITE_API_URL;
    const token = getToken();

    if (!baseUrl) {
      patchChannelState(channelUuid, {
        isLoading: false,
        error: 'Brak VITE_API_URL.',
      });
      return;
    }

    try {
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const response = await fetch(
        `${baseUrl}/chat/messages/?channel_uuid=${encodeURIComponent(channelUuid)}`,
        { headers },
      );

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`HTTP ${response.status} ${errorBody}`);
      }

      const rawData = (await response.json()) as unknown;
      const mappedMessages = mapApiMessages(channelUuid, rawData);

      const currentState = getChannelState(channelUuid);
      if (currentState.inFlightRequestId !== requestId) {
        return;
      }

      setMessagesForChannel(channelUuid, mappedMessages);
      patchChannelState(channelUuid, {
        isLoading: false,
        error: null,
        fetchedAt: Date.now(),
      });
    } catch (error) {
      patchChannelState(channelUuid, {
        isLoading: false,
        error: error instanceof Error ? error.message : 'Błąd ładowania wiadomości.',
      });
    } finally {
      delete inFlightByChannel[channelUuid];
    }
  })();

  inFlightByChannel[channelUuid] = task;
  return task;
}

export async function ensureChannelMessages(channelUuid: string): Promise<void> {
  const hasCache = channelUuid in get(messagesByChannel);
  const inFlight = inFlightByChannel[channelUuid];

  if (inFlight) {
    return inFlight;
  }

  if (!hasCache) {
    await fetchChannelMessages(channelUuid);
    return;
  }

  if (isCacheFresh(channelUuid)) {
    return;
  }

  void fetchChannelMessages(channelUuid);
}

export function addMessage(message: Message): void {
  messagesByChannel.update((current) => {
    const existing = current[message.channel_uuid] ?? [];

    if (existing.some((item) => item.uuid === message.uuid)) {
      return current;
    }

    return {
      ...current,
      [message.channel_uuid]: [...existing, message],
    };
  });

  patchChannelState(message.channel_uuid, {
    fetchedAt: Date.now(),
    error: null,
  });
}

export function setMessagesForChannel(channelUuid: string, messages: Message[]): void {
  messagesByChannel.update((current) => ({
    ...current,
    [channelUuid]: messages,
  }));
}

export function clearMessagesForChannel(channelUuid: string): void {
  messagesByChannel.update((current) => ({
    ...current,
    [channelUuid]: [],
  }));

  patchChannelState(channelUuid, {
    fetchedAt: null,
    isLoading: false,
    error: null,
    inFlightRequestId: null,
  });
}
