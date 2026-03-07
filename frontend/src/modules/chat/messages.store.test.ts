import { get } from 'svelte/store';
import type { Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Message } from '../../types/gateway';

const CHANNEL_UUID = 'channel-1';
const PAGE_LIMIT = 50;

type ApiMessage = {
  uuid: string;
  author: string;
  authorProfileDisplayName: string;
  content: string;
  createdAt: string;
};

type Cursor = {
  createdAt: string;
  uuid: string;
};

type ApiResponse = {
  items: ApiMessage[];
  has_more_older: boolean;
  has_more_newer: boolean;
  next_before: string | null;
  next_after: string | null;
};

type QueryState = {
  hasMoreNewer: boolean;
  isLoadingInitial?: boolean;
};

type StoreModule = {
  ensureChannelMessages(channelUuid: string): Promise<void>;
  loadOlderMessages(channelUuid: string): Promise<void>;
  loadNewerMessages(channelUuid: string): Promise<void>;
  addMessage(message: Message): void;
  messagesByChannel: Writable<Record<string, Message[]>>;
  channelQueryStateById: Writable<Record<string, QueryState>>;
};

function parseCursor(raw: string | null): Cursor | null {
  if (!raw) {
    return null;
  }

  const [createdAt, uuid] = raw.split('|');
  if (!createdAt || !uuid) {
    return null;
  }

  return { createdAt, uuid };
}

function makeDataset(size: number): ApiMessage[] {
  const start = Date.UTC(2026, 0, 1, 0, 0, 0);

  return Array.from({ length: size }, (_, idx) => {
    const id = idx + 1;
    return {
      uuid: `msg-${String(id).padStart(3, '0')}`,
      author: 'user-1',
      authorProfileDisplayName: 'User 1',
      content: `m-${String(id).padStart(3, '0')}`,
      createdAt: new Date(start + idx * 1000).toISOString(),
    };
  });
}

function compareByCursor(message: ApiMessage, cursor: Cursor): number {
  if (message.createdAt < cursor.createdAt) {
    return -1;
  }
  if (message.createdAt > cursor.createdAt) {
    return 1;
  }
  if (message.uuid < cursor.uuid) {
    return -1;
  }
  if (message.uuid > cursor.uuid) {
    return 1;
  }
  return 0;
}

function buildCursor(message: ApiMessage | undefined): string | null {
  if (!message) {
    return null;
  }

  return `${message.createdAt}|${message.uuid}`;
}

function createFetchMock(dataset: ApiMessage[]): ReturnType<typeof vi.fn> {
  return vi.fn(async (input: RequestInfo | URL) => {
    const rawUrl = typeof input === 'string' ? input : input.toString();
    const url = new URL(rawUrl);

    const before = parseCursor(url.searchParams.get('before'));
    const after = parseCursor(url.searchParams.get('after'));
    const limit = Number(url.searchParams.get('limit') ?? PAGE_LIMIT);

    let filtered = dataset;
    if (before) {
      filtered = dataset.filter((item) => compareByCursor(item, before) < 0);
    }
    if (after) {
      filtered = dataset.filter((item) => compareByCursor(item, after) > 0);
    }

    let pageItems: ApiMessage[];
    let hasMoreOlder = false;
    let hasMoreNewer = false;

    if (after) {
      const rows = filtered.slice(0, limit + 1);
      hasMoreNewer = rows.length > limit;
      pageItems = rows.slice(0, limit);
      const first = pageItems[0];
      hasMoreOlder = first
        ? dataset.some(
            (item) => compareByCursor(item, { createdAt: first.createdAt, uuid: first.uuid }) < 0,
          )
        : false;
    } else {
      const rowsDesc = [...filtered].reverse().slice(0, limit + 1);
      hasMoreOlder = rowsDesc.length > limit;
      pageItems = rowsDesc.slice(0, limit).reverse();
      const last = pageItems[pageItems.length - 1];
      hasMoreNewer =
        last !== undefined
          ? dataset.some(
              (item) => compareByCursor(item, { createdAt: last.createdAt, uuid: last.uuid }) > 0,
            )
          : false;
    }

    const payload: ApiResponse = {
      items: pageItems,
      has_more_older: hasMoreOlder,
      has_more_newer: hasMoreNewer,
      next_before: buildCursor(pageItems[0]),
      next_after: buildCursor(pageItems[pageItems.length - 1]),
    };

    return {
      ok: true,
      status: 200,
      json: async () => payload,
    } as Response;
  });
}

async function loadStoreModule(): Promise<StoreModule> {
  vi.resetModules();
  vi.stubEnv('VITE_API_URL', 'http://api.test');

  Object.defineProperty(globalThis, 'localStorage', {
    value: {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    },
    configurable: true,
  });

  return (await import('./messages.store')) as StoreModule;
}

describe('messages.store pagination window', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it('keeps max 300 messages and evicts from opposite side of load direction', async () => {
    const dataset = makeDataset(400);
    vi.stubGlobal('fetch', createFetchMock(dataset));

    const store = await loadStoreModule();

    await store.ensureChannelMessages(CHANNEL_UUID);
    for (let idx = 0; idx < 6; idx += 1) {
      await store.loadOlderMessages(CHANNEL_UUID);
    }

    const afterOlderLoads = get(store.messagesByChannel)[CHANNEL_UUID] ?? [];
    expect(afterOlderLoads).toHaveLength(300);
    expect(afterOlderLoads[0]?.content).toBe('m-051');
    expect(afterOlderLoads[299]?.content).toBe('m-350');

    const stateAfterOlder = get(store.channelQueryStateById)[CHANNEL_UUID];
    expect(stateAfterOlder?.hasMoreNewer).toBe(true);

    await store.loadNewerMessages(CHANNEL_UUID);

    const afterNewerLoad = get(store.messagesByChannel)[CHANNEL_UUID] ?? [];
    expect(afterNewerLoad).toHaveLength(300);
    expect(afterNewerLoad[0]?.content).toBe('m-101');
    expect(afterNewerLoad[299]?.content).toBe('m-400');
  });

  it('deduplicates messages by uuid for websocket addMessage', async () => {
    const dataset = makeDataset(60);
    vi.stubGlobal('fetch', createFetchMock(dataset));

    const store = await loadStoreModule();

    await store.ensureChannelMessages(CHANNEL_UUID);

    const sameUuid = 'msg-060';
    store.addMessage({
      uuid: sameUuid,
      channel_uuid: CHANNEL_UUID,
      author: 'User 1',
      content: 'duplicate',
      created_at: new Date().toISOString(),
    });

    const messages = get(store.messagesByChannel)[CHANNEL_UUID] ?? [];
    const occurrences = messages.filter((item) => item.uuid === sameUuid).length;
    expect(occurrences).toBe(1);
  });

  it('does not refetch when cache is still fresh (< TTL)', async () => {
    const dataset = makeDataset(80);
    const fetchMock = createFetchMock(dataset);
    vi.stubGlobal('fetch', fetchMock);

    const nowSpy = vi.spyOn(Date, 'now');
    nowSpy.mockReturnValue(1_000_000);

    const store = await loadStoreModule();
    await store.ensureChannelMessages(CHANNEL_UUID);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    nowSpy.mockReturnValue(1_030_000);
    await store.ensureChannelMessages(CHANNEL_UUID);

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('keeps data and triggers background revalidate when cache is stale (> TTL)', async () => {
    const dataset = makeDataset(80);
    const fetchMock = createFetchMock(dataset);
    vi.stubGlobal('fetch', fetchMock);

    const nowSpy = vi.spyOn(Date, 'now');
    nowSpy.mockReturnValue(1_000_000);

    const store = await loadStoreModule();
    await store.ensureChannelMessages(CHANNEL_UUID);

    const beforeStaleRefresh = (get(store.messagesByChannel)[CHANNEL_UUID] ?? []).length;
    expect(beforeStaleRefresh).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    nowSpy.mockReturnValue(1_070_000);
    await store.ensureChannelMessages(CHANNEL_UUID);
    await vi.waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    const queryState = get(store.channelQueryStateById)[CHANNEL_UUID];
    expect(queryState?.isLoadingInitial).toBe(false);
    expect((get(store.messagesByChannel)[CHANNEL_UUID] ?? []).length).toBe(beforeStaleRefresh);
  });
});
