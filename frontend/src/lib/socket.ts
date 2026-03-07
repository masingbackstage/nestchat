import { chatConnectionStatus } from '../modules/chat/messages.store';
import type { GatewayMessageEvent } from '../types/gateway';

type MessageListener = (event: GatewayMessageEvent) => void;

let socket: WebSocket | null = null;
const listeners = new Set<MessageListener>();

function createWsUrl(base: string, token: string): string {
  const normalized = base.endsWith('/') ? base.slice(0, -1) : base;
  return `${normalized}/ws/?token=${encodeURIComponent(token)}`;
}

export function connectGateway(token: string): void {
  if (
    socket &&
    (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }

  const base = import.meta.env.VITE_WS_URL;
  if (!base || !token) {
    chatConnectionStatus.set('error');
    return;
  }

  const wsUrl = createWsUrl(base, token);
  chatConnectionStatus.set('connecting');

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    chatConnectionStatus.set('connected');
  };

  socket.onclose = () => {
    chatConnectionStatus.set('disconnected');
    socket = null;
  };

  socket.onerror = () => {
    chatConnectionStatus.set('error');
  };

  socket.onmessage = (event: MessageEvent<string>) => {
    try {
      const parsed: GatewayMessageEvent = JSON.parse(event.data);
      listeners.forEach((listener) => listener(parsed));
    } catch {
      // ignore malformed messages
    }
  };
}

export function disconnectGateway(): void {
  if (!socket) {
    return;
  }

  socket.close();
  socket = null;
  chatConnectionStatus.set('disconnected');
}

export function subscribeGateway(listener: MessageListener): () => void {
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}

export function sendChatMessage(channelUuid: string, content: string): boolean {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return false;
  }

  socket.send(
    JSON.stringify({
      module: 'CHAT',
      action: 'SEND_MESSAGE',
      payload: {
        channel_uuid: channelUuid,
        content,
      },
    }),
  );

  return true;
}
