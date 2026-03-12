// Ordered by common messenger UX: faces first, then people, then objects/categories.
// Intentionally skips CJK/symbol-heavy ranges that feel "non-standard" in chat pickers.
const EMOJI_RANGES: Array<[number, number]> = [
  // Smileys & emotion
  [0x1f600, 0x1f64f],
  [0x1f910, 0x1f92f],
  [0x1f970, 0x1f97f],
  // People & body
  [0x1f44a, 0x1f450],
  [0x1f466, 0x1f487],
  [0x1f9b0, 0x1f9bf],
  [0x1f9d0, 0x1f9e6],
  // Animals & nature
  [0x1f400, 0x1f43e],
  [0x1f980, 0x1f997],
  [0x1f330, 0x1f33f],
  // Food & drink
  [0x1f345, 0x1f37f],
  [0x1f950, 0x1f96f],
  // Activities & sports
  [0x1f3a0, 0x1f3c4],
  [0x1f3c6, 0x1f3ca],
  [0x1f3cf, 0x1f3d3],
  [0x1f3f8, 0x1f3fa],
  // Travel & places
  [0x1f680, 0x1f6c5],
  // Objects
  [0x1f4a0, 0x1f4ff],
  [0x1f500, 0x1f53d],
  // Symbols commonly used in chats
  [0x1f7e0, 0x1f7eb],
];

const EXTRA_COMMON_EMOJI = ['❤️', '❣️', '✨', '⭐', '☀️', '☕', '✅', '⚠️', '❌', '⚡', '🔥'];

function buildUnicodeEmojiPicker(): string[] {
  const isEmojiPresentation = /^\p{Emoji_Presentation}$/u;
  const items: string[] = [];
  const seen = new Set<string>();

  for (const [start, end] of EMOJI_RANGES) {
    for (let codePoint = start; codePoint <= end; codePoint += 1) {
      const char = String.fromCodePoint(codePoint);
      if (!isEmojiPresentation.test(char)) {
        continue;
      }
      const emoji = char;
      if (seen.has(emoji)) {
        continue;
      }
      seen.add(emoji);
      items.push(emoji);
    }
  }

  for (const emoji of EXTRA_COMMON_EMOJI) {
    if (!seen.has(emoji)) {
      seen.add(emoji);
      items.push(emoji);
    }
  }

  return items;
}

export const UNICODE_EMOJI_PICKER = buildUnicodeEmojiPicker();
