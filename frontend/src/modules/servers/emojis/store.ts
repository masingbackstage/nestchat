import { get, writable } from 'svelte/store';
import { authFetch } from '../../../lib/auth';
import { getApiBaseUrl } from '../../../lib/url';
import type { ServerEmoji } from '../../../types/gateway';
import type { EmojisQueryState } from './types';
import { normalizeEmoji } from './utils';

const CACHE_TTL_MS = 60_000;
const defaultState: EmojisQueryState = {
  fetchedAt: null,
  isLoading: false,
  error: null,
};

const inFlightByServer = new Map<string, Promise<void>>();

export const serverEmojisByServer = writable<Record<string, ServerEmoji[]>>({});
export const serverEmojisQueryByServer = writable<Record<string, EmojisQueryState>>({});

function patchQueryState(serverUuid: string, patch: Partial<EmojisQueryState>): void {
  serverEmojisQueryByServer.update((current) => ({
    ...current,
    [serverUuid]: {
      ...(current[serverUuid] ?? defaultState),
      ...patch,
    },
  }));
}

function isFresh(serverUuid: string): boolean {
  const query = get(serverEmojisQueryByServer)[serverUuid] ?? defaultState;
  if (!query.fetchedAt) {
    return false;
  }
  return Date.now() - query.fetchedAt <= CACHE_TTL_MS;
}

export async function ensureServerEmojis(serverUuid: string, force = false): Promise<void> {
  if (!force && isFresh(serverUuid)) {
    return;
  }
  const inFlightRequest = inFlightByServer.get(serverUuid);
  if (inFlightRequest) {
    await inFlightRequest;
    return;
  }

  const baseUrl = getApiBaseUrl();
  patchQueryState(serverUuid, { isLoading: true, error: null });
  const task = (async () => {
    try {
      const response = await authFetch(`${baseUrl}/servers/${serverUuid}/emojis/`);
      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`HTTP ${response.status} ${errorBody}`);
      }
      const payload = (await response.json()) as unknown;
      const rows = Array.isArray(payload) ? payload : [];
      const emojis = rows
        .map((item) => normalizeEmoji(item as Record<string, unknown>))
        .filter((item) => item.uuid && item.name);

      serverEmojisByServer.update((current) => ({
        ...current,
        [serverUuid]: emojis,
      }));
      patchQueryState(serverUuid, {
        fetchedAt: Date.now(),
        isLoading: false,
        error: null,
      });
    } catch (error) {
      patchQueryState(serverUuid, {
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load emojis.',
      });
    } finally {
      inFlightByServer.delete(serverUuid);
    }
  })();

  inFlightByServer.set(serverUuid, task);
  await task;
}
