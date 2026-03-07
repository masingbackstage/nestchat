<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { servers } from './lib/stores/servers';
  import { activeServer, activeChannel } from './lib/stores/ui';
  import {
    connectGateway,
    disconnectGateway,
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
  import ServerList from './modules/servers/ServerList.svelte';
  import ChannelList from './modules/channels/ChannelList.svelte';
  import ChatWindow from './modules/chat/ChatWindow.svelte';

  let unsubscribeGateway: (() => void) | null = null;
  let unsubscribeGatewayReconnect: (() => void) | null = null;
  const EMPTY_CHANNEL_MARKER = '__empty__';
  const lastReadMarkerByChannel: Record<string, string | undefined> = {};

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
    const token = import.meta.env.VITE_API_TOKEN ?? localStorage.getItem('access_token');

    if (!baseUrl) {
      console.error('Brak VITE_API_URL w env.');
      servers.set([]);
      activeServer.set(null);
      activeChannel.set(null);
      return;
    }

    try {
      const response = await fetch(`${baseUrl}/servers/`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data: Server[] = await response.json();
      servers.set(data);

      const firstServer = data[0] ?? null;
      activeServer.set(firstServer);
      activeChannel.set(firstServer?.channels?.[0] ?? null);

      if (token) {
        connectGateway(token);
        unsubscribeGateway = subscribeGateway(handleGatewayEvent);
        unsubscribeGatewayReconnect = subscribeGatewayReconnect(() => {
          void resyncAfterReconnect();
        });
      }

      const channelUuids = data.flatMap((serverItem) => serverItem.channels.map((channel) => channel.uuid));
      await Promise.all(channelUuids.map((channelUuid) => fetchChannelReadState(channelUuid)));
    } catch (error) {
      console.error('Błąd ładowania serwerów:', error);
      servers.set([]);
      activeServer.set(null);
      activeChannel.set(null);
    }
  }

  onMount(loadServers);

  $: if ($activeChannel?.uuid) {
    ensureChannelMessages($activeChannel.uuid);
  }

  $: if ($activeChannel?.uuid) {
    const channelUuid = $activeChannel.uuid;
    const messages = $messagesByChannel[channelUuid] ?? [];
    const latestMessageUuid = messages[messages.length - 1]?.uuid;

    if (latestMessageUuid && lastReadMarkerByChannel[channelUuid] !== latestMessageUuid) {
      lastReadMarkerByChannel[channelUuid] = latestMessageUuid;
      void markChannelAsRead(channelUuid, latestMessageUuid);
    } else if (!latestMessageUuid && lastReadMarkerByChannel[channelUuid] !== EMPTY_CHANNEL_MARKER) {
      lastReadMarkerByChannel[channelUuid] = EMPTY_CHANNEL_MARKER;
      void fetchChannelReadState(channelUuid);
    }
  }

  onDestroy(() => {
    unsubscribeGateway?.();
    unsubscribeGatewayReconnect?.();
    disconnectGateway();
  });
</script>

<div class="flex h-screen w-full overflow-hidden bg-app-950 text-slate-100">
  <ServerList />
  <ChannelList />
  <ChatWindow />
</div>
