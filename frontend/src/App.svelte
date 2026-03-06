<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { servers } from './lib/stores/servers';
  import { activeServer, activeChannel } from './lib/stores/ui';
  import { connectGateway, disconnectGateway, subscribeGateway } from './lib/socket';
  import { addMessage } from './modules/chat/messages.store';
  import type { GatewayMessageEvent, Message, Server } from './types/gateway';
  import ServerList from './modules/servers/ServerList.svelte';
  import ChannelList from './modules/channels/ChannelList.svelte';
  import ChatWindow from './modules/chat/ChatWindow.svelte';

  let unsubscribeGateway: (() => void) | null = null;

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
      created_at: new Date().toISOString()
    };

    addMessage(message);
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
        headers: token ? { Authorization: `Bearer ${token}` } : {}
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
      }
    } catch (error) {
      console.error('Błąd ładowania serwerów:', error);
      servers.set([]);
      activeServer.set(null);
      activeChannel.set(null);
    }
  }

  onMount(loadServers);

  onDestroy(() => {
    unsubscribeGateway?.();
    disconnectGateway();
  });
</script>

<div class="flex h-screen w-full overflow-hidden bg-app-950 text-slate-100">
  <ServerList />
  <ChannelList />
  <ChatWindow />
</div>
