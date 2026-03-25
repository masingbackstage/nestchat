import { clampVoiceThreshold, DEFAULT_VOICE_THRESHOLD } from './gate';

const VOICE_SETTINGS_STORAGE_KEY = 'voice_settings_v1';

type StoredVoiceSettings = {
  threshold?: number;
};

function hasLocalStorage(): boolean {
  return typeof localStorage !== 'undefined';
}

export function loadVoiceThreshold(): number {
  if (!hasLocalStorage()) {
    return DEFAULT_VOICE_THRESHOLD;
  }

  try {
    const raw = localStorage.getItem(VOICE_SETTINGS_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_VOICE_THRESHOLD;
    }

    const parsed = JSON.parse(raw) as StoredVoiceSettings;
    return clampVoiceThreshold(parsed.threshold ?? DEFAULT_VOICE_THRESHOLD);
  } catch {
    return DEFAULT_VOICE_THRESHOLD;
  }
}

export function saveVoiceThreshold(threshold: number): void {
  if (!hasLocalStorage()) {
    return;
  }

  localStorage.setItem(
    VOICE_SETTINGS_STORAGE_KEY,
    JSON.stringify({ threshold: clampVoiceThreshold(threshold) } satisfies StoredVoiceSettings),
  );
}
