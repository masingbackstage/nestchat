export function getApiBaseUrl(): string {
  const apiBase = import.meta.env.VITE_API_URL as string | undefined;
  if (!apiBase) {
    throw new Error('Missing VITE_API_URL.');
  }
  return apiBase;
}

export function toApiAbsoluteUrl(value: string | null | undefined): string | null {
  const raw = value?.trim();
  if (!raw) {
    return null;
  }

  if (
    raw.startsWith('http://') ||
    raw.startsWith('https://') ||
    raw.startsWith('data:') ||
    raw.startsWith('blob:')
  ) {
    return raw;
  }

  let apiBase: string;
  try {
    apiBase = getApiBaseUrl();
  } catch {
    return raw;
  }

  try {
    const origin = new URL(apiBase).origin;
    return new URL(raw, origin).toString();
  } catch {
    return raw;
  }
}
