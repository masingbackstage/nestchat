const DRAFTS_STORAGE_KEY = 'chat_channel_drafts_v1';

export function loadDraftsFromStorage(): Record<string, string> {
  try {
    const raw = localStorage.getItem(DRAFTS_STORAGE_KEY);
    if (!raw) {
      return {};
    }

    const parsed = JSON.parse(raw) as Record<string, string>;
    return parsed ?? {};
  } catch {
    return {};
  }
}

export function saveDraftsToStorage(draftsByChannel: Record<string, string>): void {
  localStorage.setItem(DRAFTS_STORAGE_KEY, JSON.stringify(draftsByChannel));
}

export function setDraftValue(
  draftsByChannel: Record<string, string>,
  channelUuid: string,
  value: string,
): Record<string, string> {
  if (value.trim().length === 0) {
    return Object.fromEntries(
      Object.entries(draftsByChannel).filter(([uuid]) => uuid !== channelUuid),
    );
  }

  return {
    ...draftsByChannel,
    [channelUuid]: value,
  };
}
