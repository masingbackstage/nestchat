<script lang="ts">
  import { onMount } from 'svelte';
  import { servers } from './lib/stores/servers';
  import { activeServer, activeChannel } from './lib/stores/ui';
  import type { Server } from './types/gateway';
  import ServerList from './modules/servers/ServerList.svelte';
  import ChannelList from './modules/channels/ChannelList.svelte';
  import ChatWindow from './modules/chat/ChatWindow.svelte';

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
    } catch (error) {
      console.error('Błąd ładowania serwerów:', error);
      servers.set([]);
      activeServer.set(null);
      activeChannel.set(null);
    }
  }

  onMount(loadServers);
</script>

<div class="flex h-screen w-full overflow-hidden bg-app-950 text-slate-100">
  <ServerList />
  <ChannelList />
  <ChatWindow />
</div>
