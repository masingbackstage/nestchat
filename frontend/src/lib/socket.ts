import { chatConnectionStatus } from '../modules/chat/messages.store';
import type { GatewayMessageEvent } from '../types/gateway';

type MessageListener = (event: GatewayMessageEvent) => void;
type ReconnectListener = () => void;
type TokenProvider = () => string | null | Promise<string | null>;
type AuthFailureHandler = () => void;

let socket: WebSocket | null = null;
const listeners = new Set<MessageListener>();
const reconnectListeners = new Set<ReconnectListener>();
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempt = 0;
let manuallyDisconnected = false;
let currentToken: string | null = null;
let hasEverConnected = false;
let tokenProvider: TokenProvider | null = null;
let authFailureHandler: AuthFailureHandler | null = null;
const pendingChannelJoins = new Set<string>();

const RECONNECT_BASE_DELAY_MS = 1_000;
const RECONNECT_MAX_DELAY_MS = 10_000;

function createWsUrl(base: string, token: string): string {
  const normalized = base.endsWith('/') ? base.slice(0, -1) : base;
  return `${normalized}/ws/?token=${encodeURIComponent(token)}`;
}

function sendJoinChannelRequest(channelUuid: string): void {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return;
  }

  socket.send(
    JSON.stringify({
      module: 'CHAT',
      action: 'JOIN_CHANNEL',
      payload: {
        channel_uuid: channelUuid,
      },
    }),
  );
}

function flushPendingChannelJoins(): void {
  for (const channelUuid of pendingChannelJoins) {
    sendJoinChannelRequest(channelUuid);
  }
}

export function connectGateway(token: string): void {
  currentToken = token;
  manuallyDisconnected = false;

  if (
    socket &&
    (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }

  const base = import.meta.env.VITE_WS_URL;
  if (!base || !currentToken) {
    chatConnectionStatus.set('error');
    return;
  }

  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  const wsUrl = createWsUrl(base, currentToken);
  chatConnectionStatus.set('connecting');

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    const shouldNotifyReconnect = hasEverConnected;
    hasEverConnected = true;
    reconnectAttempt = 0;
    chatConnectionStatus.set('connected');
    flushPendingChannelJoins();
    if (shouldNotifyReconnect) {
      reconnectListeners.forEach((listener) => listener());
    }
  };

  socket.onclose = () => {
    chatConnectionStatus.set('disconnected');
    socket = null;
    if (!manuallyDisconnected) {
      scheduleReconnect();
    }
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
  manuallyDisconnected = true;
  currentToken = null;
  pendingChannelJoins.clear();
  reconnectAttempt = 0;
  hasEverConnected = false;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  if (!socket) {
    return;
  }

  socket.close();
  socket = null;
  chatConnectionStatus.set('disconnected');
}

export function setGatewayTokenProvider(provider: TokenProvider): void {
  tokenProvider = provider;
}

export function setGatewayAuthFailureHandler(handler: AuthFailureHandler | null): void {
  authFailureHandler = handler;
}

export function subscribeGateway(listener: MessageListener): () => void {
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}

export function subscribeGatewayReconnect(listener: ReconnectListener): () => void {
  reconnectListeners.add(listener);

  return () => {
    reconnectListeners.delete(listener);
  };
}

export function sendChatMessage(channelUuid: string, content: string, clientId?: string): boolean {
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
        ...(clientId ? { client_id: clientId } : {}),
      },
    }),
  );

  return true;
}

export function sendEditMessage(messageUuid: string, content: string): boolean {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return false;
  }

  socket.send(
    JSON.stringify({
      module: 'CHAT',
      action: 'EDIT_MESSAGE',
      payload: {
        message_uuid: messageUuid,
        content,
      },
    }),
  );

  return true;
}

export function sendDeleteMessage(messageUuid: string): boolean {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return false;
  }

  socket.send(
    JSON.stringify({
      module: 'CHAT',
      action: 'DELETE_MESSAGE',
      payload: {
        message_uuid: messageUuid,
      },
    }),
  );

  return true;
}

export function joinGatewayChannel(channelUuid: string): boolean {
  pendingChannelJoins.add(channelUuid);
  const isOpen = Boolean(socket && socket.readyState === WebSocket.OPEN);
  if (isOpen) {
    sendJoinChannelRequest(channelUuid);
  }
  return isOpen;
}

function scheduleReconnect(): void {
  if ((!currentToken && !tokenProvider) || reconnectTimer) {
    return;
  }

  const delayMs = Math.min(RECONNECT_MAX_DELAY_MS, RECONNECT_BASE_DELAY_MS * 2 ** reconnectAttempt);
  reconnectAttempt += 1;

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (manuallyDisconnected) {
      return;
    }

    if (tokenProvider) {
      void refreshTokenAndReconnect();
      return;
    }

    if (currentToken) {
      connectGateway(currentToken);
    }
  }, delayMs);
}

async function refreshTokenAndReconnect(): Promise<void> {
  if (!tokenProvider) {
    return;
  }

  const refreshedToken = await tokenProvider();
  if (!refreshedToken) {
    chatConnectionStatus.set('error');
    manuallyDisconnected = true;
    authFailureHandler?.();
    return;
  }

  connectGateway(refreshedToken);
}
