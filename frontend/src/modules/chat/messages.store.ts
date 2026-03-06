import { writable } from 'svelte/store';
import type { Message } from '../../types/gateway';

type MessagesByChannel = Record<string, Message[]>;

type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error';

export const messagesByChannel = writable<MessagesByChannel>({});
export const chatConnectionStatus = writable<ConnectionStatus>('idle');

export function addMessage(message: Message): void {
  messagesByChannel.update((current) => {
    const existing = current[message.channel_uuid] ?? [];

    if (existing.some((item) => item.uuid === message.uuid)) {
      return current;
    }

    return {
      ...current,
      [message.channel_uuid]: [...existing, message]
    };
  });
}

export function clearMessagesForChannel(channelUuid: string): void {
  messagesByChannel.update((current) => ({
    ...current,
    [channelUuid]: []
  }));
}
