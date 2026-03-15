import { getApiBaseUrl } from '../../lib/url';

type RegistrationErrorPayload = Record<string, string[] | string>;

const REGISTRATION_ERROR_KEYS = [
  'password1',
  'password2',
  'email',
  'displayName',
  'display_name',
  'nonFieldErrors',
  'non_field_errors',
  'detail',
] as const;

export async function registerWithPassword(payload: {
  email: string;
  password: string;
  confirmPassword: string;
  displayName: string;
}): Promise<{ ok: true } | { ok: false; error: string }> {
  const response = await fetch(`${getApiBaseUrl()}/auth/registration/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: payload.email,
      password1: payload.password,
      password2: payload.confirmPassword,
      displayName: payload.displayName,
    }),
  });

  if (response.ok) {
    return { ok: true };
  }

  try {
    const errorPayload = (await response.json()) as RegistrationErrorPayload;
    const firstEntry =
      REGISTRATION_ERROR_KEYS.map((key) => errorPayload[key]).find((value) => value !== undefined) ??
      Object.values(errorPayload)[0];

    if (Array.isArray(firstEntry) && firstEntry.length > 0) {
      return { ok: false, error: firstEntry[0] ?? 'Registration failed.' };
    }

    if (typeof firstEntry === 'string') {
      return { ok: false, error: firstEntry };
    }
  } catch {
    // Fall back to HTTP status below.
  }

  return { ok: false, error: `HTTP ${response.status}` };
}
