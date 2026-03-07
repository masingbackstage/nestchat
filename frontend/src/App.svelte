<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { authFetch, clearAuthTokens, getValidAccessToken } from './lib/auth';
  import { servers } from './lib/stores/servers';
  import { activeServer, activeChannel } from './lib/stores/ui';
  import {
    connectGateway,
    disconnectGateway,
    setGatewayTokenProvider,
    subscribeGateway,
    subscribeGatewayReconnect,
  } from './lib/socket';
  import {
    addMessage,
    ensureChannelMessages,
    fetchChannelReadState,
    incrementUnreadCount,
    markChannelAsRead,
    messagesByChannel,
    syncChannelFromLatestCursor,
  } from './modules/chat/messages.store';
  import type { GatewayMessageEvent, Message, Server } from './types/gateway';
  import LoginForm from './modules/auth/LoginForm.svelte';
  import RegisterForm from './modules/auth/RegisterForm.svelte';
  import ServerList from './modules/servers/ServerList.svelte';
  import ChannelList from './modules/channels/ChannelList.svelte';
  import ChatWindow from './modules/chat/ChatWindow.svelte';

  let unsubscribeGateway: (() => void) | null = null;
  let unsubscribeGatewayReconnect: (() => void) | null = null;
  const EMPTY_CHANNEL_MARKER = '__empty__';
  const READ_STATE_TTL_MS = 30_000;
  const lastReadMarkerByChannel: Record<string, string | undefined> = {};
  const readStateFetchedAtByChannel: Record<string, number | undefined> = {};
  let isBootstrapping = true;
  let isAuthenticated = false;
  let authMode: 'login' | 'register' = 'login';

  function handleGatewayEvent(event: GatewayMessageEvent): void {
    const moduleName = String(event.module ?? '').toLowerCase();
    const actionName = String(event.action ?? '').toLowerCase();

    if (moduleName !== 'chat' || actionName !== 'new_message') {
      return;
    }

    const payload = event.payload as {
      id: string;
      channel_id?: string;
      channel_uuid?: string;
      content: string;
      author: string;
    };

    const channelUuid = payload.channel_id ?? payload.channel_uuid;
    if (!channelUuid) {
      return;
    }

    const message: Message = {
      uuid: payload.id,
      channel_uuid: channelUuid,
      content: payload.content,
      author: payload.author,
      created_at: new Date().toISOString(),
    };

    addMessage(message);
    if ($activeChannel?.uuid !== channelUuid) {
      incrementUnreadCount(channelUuid);
    }
  }

  async function resyncAfterReconnect(): Promise<void> {
    const channels = Object.keys($messagesByChannel);
    await Promise.all(channels.map((channelUuid) => syncChannelFromLatestCursor(channelUuid)));
  }

  async function loadServers(): Promise<void> {
    const baseUrl = import.meta.env.VITE_API_URL;

    if (!baseUrl) {
      console.error('Brak VITE_API_URL w env.');
      servers.set([]);
      activeServer.set(null);
      activeChannel.set(null);
      return;
    }

    try {
      const response = await authFetch(`${baseUrl}/servers/`);

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          isAuthenticated = false;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      const data: Server[] = await response.json();
      servers.set(data);

      const firstServer = data[0] ?? null;
      activeServer.set(firstServer);
      activeChannel.set(firstServer?.channels?.[0] ?? null);

      setGatewayTokenProvider(getValidAccessToken);
      const token = await getValidAccessToken();
      if (token) {
        isAuthenticated = true;
        connectGateway(token);
        unsubscribeGateway = subscribeGateway(handleGatewayEvent);
        unsubscribeGatewayReconnect = subscribeGatewayReconnect(() => {
          void resyncAfterReconnect();
        });
      }

    } catch (error) {
      console.error('Błąd ładowania serwerów:', error);
      servers.set([]);
      activeServer.set(null);
      activeChannel.set(null);
    }
  }

  async function bootstrapApp(): Promise<void> {
    isBootstrapping = true;
    const token = await getValidAccessToken();

    if (!token) {
      isAuthenticated = false;
      isBootstrapping = false;
      return;
    }

    isAuthenticated = true;
    await loadServers();
    isBootstrapping = false;
  }

  onMount(bootstrapApp);

  $: if ($activeChannel?.uuid) {
    ensureChannelMessages($activeChannel.uuid);
  }

  $: if ($activeServer?.channels?.length) {
    const now = Date.now();
    for (const channel of $activeServer.channels) {
      const fetchedAt = readStateFetchedAtByChannel[channel.uuid] ?? 0;
      if (now - fetchedAt <= READ_STATE_TTL_MS) {
        continue;
      }
      readStateFetchedAtByChannel[channel.uuid] = now;
      void fetchChannelReadState(channel.uuid);
    }
  }

  $: if ($activeChannel?.uuid) {
    const channelUuid = $activeChannel.uuid;
    const messages = $messagesByChannel[channelUuid] ?? [];
    const latestMessageUuid = messages[messages.length - 1]?.uuid;

    if (latestMessageUuid && lastReadMarkerByChannel[channelUuid] !== latestMessageUuid) {
      lastReadMarkerByChannel[channelUuid] = latestMessageUuid;
      void markChannelAsRead(channelUuid, latestMessageUuid);
      readStateFetchedAtByChannel[channelUuid] = Date.now();
    } else if (!latestMessageUuid && lastReadMarkerByChannel[channelUuid] !== EMPTY_CHANNEL_MARKER) {
      lastReadMarkerByChannel[channelUuid] = EMPTY_CHANNEL_MARKER;
      readStateFetchedAtByChannel[channelUuid] = Date.now();
      void fetchChannelReadState(channelUuid);
    }
  }

  onDestroy(() => {
    unsubscribeGateway?.();
    unsubscribeGatewayReconnect?.();
    disconnectGateway();
  });

  async function handleAuthenticated(): Promise<void> {
    isAuthenticated = true;
    authMode = 'login';
    await loadServers();
  }

  function handleLogout(): void {
    clearAuthTokens();
    isAuthenticated = false;
    servers.set([]);
    activeServer.set(null);
    activeChannel.set(null);
    unsubscribeGateway?.();
    unsubscribeGatewayReconnect?.();
    unsubscribeGateway = null;
    unsubscribeGatewayReconnect = null;
    disconnectGateway();
  }
</script>

{#if isBootstrapping}
  <div class="flex h-screen w-full items-center justify-center bg-app-950 text-sm text-slate-400">
    Ładowanie...
  </div>
{:else if !isAuthenticated}
  {#if authMode === 'login'}
    <LoginForm
      on:authenticated={handleAuthenticated}
      on:switchToRegister={() => {
        authMode = 'register';
      }}
    />
  {:else}
    <RegisterForm
      on:authenticated={handleAuthenticated}
      on:switchToLogin={() => {
        authMode = 'login';
      }}
    />
  {/if}
{:else}
  <div class="flex h-screen w-full overflow-hidden bg-app-950 text-slate-100">
    <button
      type="button"
      on:click={handleLogout}
      class="absolute right-3 top-3 z-10 rounded border border-slate-700 bg-app-900 px-3 py-1 text-xs text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
    >
      Wyloguj
    </button>
    <ServerList />
    <ChannelList />
    <ChatWindow />
  </div>
{/if}
