import { beforeEach, describe, expect, it, vi } from 'vitest';

type StorageMock = {
  getItem: ReturnType<typeof vi.fn>;
  setItem: ReturnType<typeof vi.fn>;
  removeItem: ReturnType<typeof vi.fn>;
  clear: ReturnType<typeof vi.fn>;
};

function mockLocalStorage(initial: Record<string, string> = {}): StorageMock {
  const state = new Map(Object.entries(initial));
  const localStorageMock: StorageMock = {
    getItem: vi.fn((key: string) => state.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      state.set(key, value);
    }),
    removeItem: vi.fn((key: string) => {
      state.delete(key);
    }),
    clear: vi.fn(() => {
      state.clear();
    }),
  };

  Object.defineProperty(globalThis, 'localStorage', {
    value: localStorageMock,
    configurable: true,
  });

  return localStorageMock;
}

describe('auth session flow', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_API_URL', 'http://api.test');
  });

  it('retries request after 401 when refresh succeeds', async () => {
    mockLocalStorage({
      access_token: 'old-access',
      refresh_token: 'old-refresh',
    });

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 401 } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access: 'new-access', refresh: 'new-refresh' }),
      } as Response)
      .mockResolvedValueOnce({ ok: true, status: 200 } as Response);

    vi.stubGlobal('fetch', fetchMock);

    const { authFetch } = await import('./auth');
    const response = await authFetch('http://api.test/protected/');

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect((fetchMock.mock.calls[2]?.[1] as RequestInit)?.headers).toBeDefined();
  });

  it('calls auth failure handler when refresh fails', async () => {
    mockLocalStorage({
      access_token: 'old-access',
      refresh_token: 'old-refresh',
    });

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 401 } as Response)
      .mockResolvedValueOnce({ ok: false, status: 401 } as Response);

    vi.stubGlobal('fetch', fetchMock);

    const onFailure = vi.fn();
    const { authFetch, setAuthFailureHandler } = await import('./auth');
    setAuthFailureHandler(onFailure);

    await authFetch('http://api.test/protected/');

    expect(onFailure).toHaveBeenCalledTimes(1);
  });

  it('logoutCurrentSession returns error and keeps tokens when request fails', async () => {
    const localStorageMock = mockLocalStorage({
      access_token: 'old-access',
      refresh_token: 'old-refresh',
    });

    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('network error')));

    const { logoutCurrentSession } = await import('./auth');
    const result = await logoutCurrentSession();

    expect(result.ok).toBe(false);
    expect(result.error).toBeDefined();
    expect(localStorageMock.removeItem).not.toHaveBeenCalledWith('access_token');
    expect(localStorageMock.removeItem).not.toHaveBeenCalledWith('refresh_token');
  });

  it('logoutCurrentSession succeeds without clearing tokens', async () => {
    const localStorageMock = mockLocalStorage({
      access_token: 'old-access',
      refresh_token: 'old-refresh',
    });

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
      } as Response),
    );

    const { logoutCurrentSession } = await import('./auth');
    const result = await logoutCurrentSession();

    expect(result.ok).toBe(true);
    expect(localStorageMock.removeItem).not.toHaveBeenCalled();
  });
});
