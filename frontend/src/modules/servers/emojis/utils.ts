import type { ServerEmoji } from '../../../types/gateway';

export function normalizeEmoji(raw: Record<string, unknown>): ServerEmoji {
  return {
    uuid: String(raw.uuid ?? ''),
    name: String(raw.name ?? ''),
    token: String(raw.token ?? `:${String(raw.name ?? '')}:`),
    imageUrl:
      (raw.imageUrl as string | null | undefined) ??
      (raw.image_url as string | null | undefined) ??
      null,
    image_url:
      (raw.image_url as string | null | undefined) ??
      (raw.imageUrl as string | null | undefined) ??
      null,
    isAnimated:
      (raw.isAnimated as boolean | undefined) ?? (raw.is_animated as boolean | undefined) ?? false,
    is_animated:
      (raw.is_animated as boolean | undefined) ?? (raw.isAnimated as boolean | undefined) ?? false,
  };
}
