const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const REFRESH_ENDPOINT = '/auth/token/refresh/';
const LOGIN_ENDPOINT = '/auth/login/';
const LOGOUT_SESSION_ENDPOINT = '/auth/logout-session/';
const LOGOUT_ALL_ENDPOINT = '/auth/logout-all/';
const EXPIRY_LEEWAY_SECONDS = 30;

let refreshPromise: Promise<string | null> | null = null;
let authFailureHandler: (() => void) | null = null;

type AuthActionResult = {
  ok: boolean;
  error?: string;
};

function getBaseUrl(): string | null {
  return import.meta.env.VITE_API_URL ?? null;
}

function getEnvToken(): string | null {
  return import.meta.env.VITE_API_TOKEN ?? null;
}

export function getStoredAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getCurrentUserUuid(): string | null {
  const token = getStoredAccessToken();
  if (!token) {
    return null;
  }

  try {
    const payloadBase64 = token.split('.')[1];
    if (!payloadBase64) {
      return null;
    }
    const payloadJson = atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(payloadJson) as { user_uuid?: string; userUuid?: string };
    return payload.user_uuid ?? payload.userUuid ?? null;
  } catch {
    return null;
  }
}

function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function setStoredAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

function setStoredRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

function clearStoredTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function clearAuthTokens(): void {
  clearStoredTokens();
}

export function setAuthFailureHandler(handler: (() => void) | null): void {
  authFailureHandler = handler;
}

function notifyAuthFailure(): void {
  authFailureHandler?.();
}

function parseJwtExp(token: string): number | null {
  try {
    const payloadBase64 = token.split('.')[1];
    if (!payloadBase64) {
      return null;
    }
    const payloadJson = atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(payloadJson) as { exp?: number };
    return typeof payload.exp === 'number' ? payload.exp : null;
  } catch {
    return null;
  }
}

function isAccessTokenExpired(token: string): boolean {
  const exp = parseJwtExp(token);
  if (!exp) {
    return false;
  }

  const nowSeconds = Math.floor(Date.now() / 1000);
  return nowSeconds >= exp - EXPIRY_LEEWAY_SECONDS;
}

export async function refreshAccessToken(): Promise<string | null> {
  const envToken = getEnvToken();
  if (envToken) {
    return envToken;
  }

  if (refreshPromise) {
    return refreshPromise;
  }

  const baseUrl = getBaseUrl();
  const refreshToken = getStoredRefreshToken();
  if (!baseUrl || !refreshToken) {
    notifyAuthFailure();
    return null;
  }

  refreshPromise = (async () => {
    const response = await fetch(`${baseUrl}${REFRESH_ENDPOINT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!response.ok) {
      clearStoredTokens();
      notifyAuthFailure();
      return null;
    }

    const payload = (await response.json()) as {
      access?: string;
      refresh?: string;
    };

    if (!payload.access) {
      clearStoredTokens();
      notifyAuthFailure();
      return null;
    }

    setStoredAccessToken(payload.access);
    if (payload.refresh) {
      setStoredRefreshToken(payload.refresh);
    }

    return payload.access;
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

async function extractErrorDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as {
      detail?: string;
      nonFieldErrors?: string[];
      non_field_errors?: string[];
    };
    return (
      payload.detail ??
      payload.nonFieldErrors?.[0] ??
      payload.non_field_errors?.[0] ??
      `HTTP ${response.status}`
    );
  } catch {
    return `HTTP ${response.status}`;
  }
}

export async function logoutCurrentSession(): Promise<AuthActionResult> {
  const baseUrl = getBaseUrl();
  const refreshToken = getStoredRefreshToken();
  const accessToken = getStoredAccessToken();

  if (!baseUrl) {
    return { ok: false, error: 'Missing VITE_API_URL.' };
  }
  if (!refreshToken) {
    return { ok: false, error: 'Missing refresh token.' };
  }
  if (!accessToken) {
    return { ok: false, error: 'Missing access token.' };
  }

  try {
    const headers = new Headers({
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    });

    const response = await fetch(`${baseUrl}${LOGOUT_SESSION_ENDPOINT}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!response.ok) {
      return {
        ok: false,
        error: await extractErrorDetail(response),
      };
    }

    return { ok: true };
  } catch {
    return { ok: false, error: 'Network error during logout.' };
  }
}

export async function logoutAllSessions(): Promise<AuthActionResult> {
  const baseUrl = getBaseUrl();
  const accessToken = getStoredAccessToken();

  if (!baseUrl) {
    return { ok: false, error: 'Missing VITE_API_URL.' };
  }
  if (!accessToken) {
    return { ok: false, error: 'Missing access token.' };
  }

  try {
    const response = await fetch(`${baseUrl}${LOGOUT_ALL_ENDPOINT}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      return {
        ok: false,
        error: await extractErrorDetail(response),
      };
    }

    return { ok: true };
  } catch {
    return { ok: false, error: 'Network error during logout from all sessions.' };
  }
}

export async function loginWithPassword(
  email: string,
  password: string,
): Promise<{ ok: boolean; error?: string }> {
  const baseUrl = getBaseUrl();
  if (!baseUrl) {
    return { ok: false, error: 'Missing VITE_API_URL.' };
  }

  const response = await fetch(`${baseUrl}${LOGIN_ENDPOINT}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const fallbackError = `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as {
        detail?: string;
        non_field_errors?: string[];
      };
      const detail = payload.detail ?? payload.non_field_errors?.[0] ?? fallbackError;
      return { ok: false, error: detail };
    } catch {
      return { ok: false, error: fallbackError };
    }
  }

  const payload = (await response.json()) as {
    access?: string;
    refresh?: string;
  };

  if (!payload.access || !payload.refresh) {
    clearStoredTokens();
    return {
      ok: false,
      error: 'Invalid login response (missing access/refresh).',
    };
  }

  setStoredAccessToken(payload.access);
  setStoredRefreshToken(payload.refresh);
  return { ok: true };
}

export async function getValidAccessToken(): Promise<string | null> {
  const envToken = getEnvToken();
  if (envToken) {
    return envToken;
  }

  const accessToken = getStoredAccessToken();
  if (accessToken && !isAccessTokenExpired(accessToken)) {
    return accessToken;
  }

  return refreshAccessToken();
}

export async function authFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
  retryOnUnauthorized = true,
): Promise<Response> {
  const headers = new Headers(init.headers ?? {});

  if (!headers.has('Authorization')) {
    const token = await getValidAccessToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  let response = await fetch(input, {
    ...init,
    headers,
  });

  if (response.status !== 401 || !retryOnUnauthorized) {
    return response;
  }

  const refreshedToken = await refreshAccessToken();
  if (!refreshedToken) {
    return response;
  }

  headers.set('Authorization', `Bearer ${refreshedToken}`);
  response = await fetch(input, {
    ...init,
    headers,
  });

  return response;
}
