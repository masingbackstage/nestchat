export type CustomEmojiOption = {
  token: string;
  label: string;
  imageUrl: string | null;
};

export function getInitials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/).filter(Boolean).slice(0, 2);
  if (parts.length === 0) {
    return '?';
  }

  return parts.map((part) => part[0]?.toUpperCase() ?? '').join('');
}

export function filterCustomEmojis(
  customEmojis: CustomEmojiOption[],
  normalizedSearch: string,
): CustomEmojiOption[] {
  if (normalizedSearch.length === 0) {
    return customEmojis;
  }

  return customEmojis.filter(
    (item) =>
      item.label.toLowerCase().includes(normalizedSearch) ||
      item.token.toLowerCase().includes(normalizedSearch),
  );
}

export function filterUnicodeEmojis(unicodeEmojis: string[], normalizedSearch: string): string[] {
  if (normalizedSearch.length === 0) {
    return unicodeEmojis;
  }

  return unicodeEmojis.filter((emoji) => emoji.includes(normalizedSearch));
}

export function formatMessageTime(value: string | undefined): string {
  return value
    ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '--:--';
}

export function findCustomEmojiByToken(
  customEmojis: CustomEmojiOption[],
  token: string,
): CustomEmojiOption | null {
  return customEmojis.find((item) => item.token === token) ?? null;
}
