<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
import {
  authFetch,
  clearAuthTokens,
  getValidAccessToken,
  logoutAllSessions,
  logoutCurrentSession,
  setAuthFailureHandler,
} from './lib/auth';
import { pushToast } from './lib/stores/toast';
  import { servers } from './lib/stores/servers';
  import { activeServer, activeChannel } from './lib/stores/ui';
  import {
    connectGateway,
    disconnectGateway,
    joinGatewayChannel,
    setGatewayAuthFailureHandler,
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
    resetChatState,
    softDeleteMessage,
    syncChannelFromLatestCursor,
    updateMessage,
  } from './modules/chat/messages.store';
  import type { GatewayMessageEvent, Message, Server } from './types/gateway';
  import LoginForm from './modules/auth/LoginForm.svelte';
  import RegisterForm from './modules/auth/RegisterForm.svelte';
  import SettingsModal from './modules/auth/SettingsModal.svelte';
import LandingPage from './modules/landing/LandingPage.svelte';
import ServerList from './modules/servers/ServerList.svelte';
import ChannelList from './modules/channels/ChannelList.svelte';
import ChatWindow from './modules/chat/ChatWindow.svelte';
import ToastViewport from './modules/shared/ToastViewport.svelte';

  let unsubscribeGateway: (() => void) | null = null;
  let unsubscribeGatewayReconnect: (() => void) | null = null;
  const EMPTY_CHANNEL_MARKER = '__empty__';
  const READ_STATE_TTL_MS = 30_000;
  const lastReadMarkerByChannel: Record<string, string | undefined> = {};
  const readStateFetchedAtByChannel: Record<string, number | undefined> = {};
  let isBootstrapping = true;
  let isAuthenticated = false;
  let isSettingsOpen = false;
  let isSettingsSubmitting = false;
  let authMode: 'login' | 'register' = 'login';
  let routePath = '/';

  function getCurrentPath(): string {
    return window.location.pathname === '/app' ? '/app' : '/';
  }

  function syncRouteFromLocation(): void {
    routePath = getCurrentPath();
    const mode = new URLSearchParams(window.location.search).get('mode');
    if (mode === 'register') {
      authMode = 'register';
      return;
    }
    if (mode === 'login' || routePath === '/app') {
      authMode = 'login';
    }
  }

  function navigate(path: '/' | '/app', mode?: 'login' | 'register'): void {
    const search = path === '/app' && mode ? `?mode=${mode}` : '';
    window.history.pushState({}, '', `${path}${search}`);
    routePath = path;
    if (mode) {
      authMode = mode;
    }
  }

  function clearReadStateCache(): void {
    for (const key of Object.keys(lastReadMarkerByChannel)) {
      delete lastReadMarkerByChannel[key];
    }
    for (const key of Object.keys(readStateFetchedAtByChannel)) {
      delete readStateFetchedAtByChannel[key];
    }
  }

  function tearDownGatewaySubscriptions(): void {
    unsubscribeGateway?.();
    unsubscribeGatewayReconnect?.();
    unsubscribeGateway = null;
    unsubscribeGatewayReconnect = null;
    disconnectGateway();
  }

  function applyUnauthenticatedState(): void {
    isAuthenticated = false;
    servers.set([]);
    activeServer.set(null);
    activeChannel.set(null);
    clearReadStateCache();
    resetChatState();
    tearDownGatewaySubscriptions();
    isSettingsOpen = false;
    isSettingsSubmitting = false;
    navigate('/app', 'login');
  }

  function handleGatewayEvent(event: GatewayMessageEvent): void {
    const moduleName = String(event.module ?? '').toLowerCase();
    const actionName = String(event.action ?? '').toLowerCase();

    if (moduleName === 'system' && actionName === 'error') {
      const payload = event.payload as { code?: string; detail?: string };
      if (payload.code === 'permission_denied' || payload.code === 'not_found') {
        pushToast({
          type: 'error',
          message: payload.detail ?? 'Błąd uprawnień kanału.',
        });
      }
      return;
    }

    if (moduleName !== 'chat') {
      return;
    }

    const payload = event.payload as {
      uuid?: string;
      id?: string;
      channel_id?: string;
      channel_uuid?: string;
      channelUuid?: string;
      content: string;
      author: string;
      author_uuid?: string;
      author_profile_display_name?: string;
      authorProfileDisplayName?: string;
      is_deleted?: boolean;
      isDeleted?: boolean;
      is_edited?: boolean;
      isEdited?: boolean;
      edited_at?: string | null;
      editedAt?: string | null;
      updated_at?: string;
      updatedAt?: string;
      created_at?: string;
      createdAt?: string;
      client_id?: string;
      clientId?: string;
    };
    const channelUuid = payload.channel_id ?? payload.channel_uuid ?? payload.channelUuid;

    if (actionName === 'new_message') {
      if (!channelUuid) {
        return;
      }

      const message: Message = {
        uuid: payload.id ?? payload.uuid ?? '',
        channel_uuid: channelUuid,
        content: payload.content,
        author:
          payload.authorProfileDisplayName ??
          payload.author_profile_display_name ??
          payload.author,
        author_uuid: payload.author_uuid ?? (payload.author ? String(payload.author) : undefined),
        is_deleted: Boolean(payload.isDeleted ?? payload.is_deleted ?? false),
        is_edited: Boolean(payload.isEdited ?? payload.is_edited ?? false),
        edited_at: payload.editedAt ?? payload.edited_at ?? null,
        created_at: payload.createdAt ?? payload.created_at ?? new Date().toISOString(),
        updated_at: payload.updatedAt ?? payload.updated_at,
        client_id: payload.client_id ?? payload.clientId,
      };

      addMessage(message);
      if ($activeChannel?.uuid !== channelUuid) {
        incrementUnreadCount(channelUuid);
      }
      return;
    }

    if ((actionName === 'message_updated' || actionName === 'message_deleted') && channelUuid) {
      const message: Message = {
        uuid: payload.uuid ?? payload.id ?? '',
        channel_uuid: channelUuid,
        content: payload.content ?? '',
        author:
          payload.authorProfileDisplayName ??
          payload.author_profile_display_name ??
          String(payload.author ?? ''),
        author_uuid: payload.author ? String(payload.author) : undefined,
        is_deleted: Boolean(payload.isDeleted ?? payload.is_deleted ?? false),
        is_edited: Boolean(payload.isEdited ?? payload.is_edited ?? false),
        edited_at: payload.editedAt ?? payload.edited_at ?? null,
        created_at: payload.createdAt ?? payload.created_at,
        updated_at: payload.updatedAt ?? payload.updated_at,
      };

      if (actionName === 'message_deleted') {
        softDeleteMessage(message);
      } else {
        updateMessage(message);
      }
    }
  }

  async function resyncAfterReconnect(): Promise<void> {
    const channels = Object.keys($messagesByChannel);
    await Promise.all(channels.map((channelUuid) => syncChannelFromLatestCursor(channelUuid)));
    if ($activeServer?.channels?.length) {
      for (const channel of $activeServer.channels) {
        joinGatewayChannel(channel.uuid);
      }
    } else if ($activeChannel?.uuid) {
      joinGatewayChannel($activeChannel.uuid);
    }
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
          applyUnauthenticatedState();
          return;
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

  onMount(() => {
    syncRouteFromLocation();
    setAuthFailureHandler(applyUnauthenticatedState);
    setGatewayAuthFailureHandler(applyUnauthenticatedState);
    window.addEventListener('popstate', syncRouteFromLocation);
    void bootstrapApp();

    return () => {
      window.removeEventListener('popstate', syncRouteFromLocation);
      setAuthFailureHandler(null);
      setGatewayAuthFailureHandler(null);
    };
  });

  $: if ($activeChannel?.uuid) {
    ensureChannelMessages($activeChannel.uuid);
    joinGatewayChannel($activeChannel.uuid);
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
    tearDownGatewaySubscriptions();
  });

  async function handleAuthenticated(): Promise<void> {
    isAuthenticated = true;
    authMode = 'login';
    navigate('/app');
    await loadServers();
  }

  async function handleLogout(): Promise<void> {
    isSettingsSubmitting = true;
    const result = await logoutCurrentSession();
    isSettingsSubmitting = false;
    if (!result.ok) {
      pushToast({
        type: 'error',
        message: result.error ?? 'Nie udało się wylogować z tego urządzenia.',
      });
      return;
    }
    clearAuthTokens();
    pushToast({
      type: 'success',
      message: 'Wylogowano z tego urządzenia.',
    });
    applyUnauthenticatedState();
  }

  async function handleLogoutAllSessions(): Promise<void> {
    isSettingsSubmitting = true;
    const result = await logoutAllSessions();
    isSettingsSubmitting = false;
    if (!result.ok) {
      pushToast({
        type: 'error',
        message: result.error ?? 'Nie udało się wylogować ze wszystkich urządzeń.',
      });
      return;
    }
    clearAuthTokens();
    pushToast({
      type: 'success',
      message: 'Wylogowano ze wszystkich urządzeń.',
    });
    applyUnauthenticatedState();
  }
</script>

{#if isBootstrapping}
  <div class="flex h-screen w-full items-center justify-center bg-app-950 text-sm text-slate-400">
    Ładowanie...
  </div>
{:else}
  {#if routePath === '/'}
    <LandingPage
      on:startLogin={() => {
        navigate('/app', 'login');
      }}
      on:startRegister={() => {
        navigate('/app', 'register');
      }}
    />
  {:else if !isAuthenticated}
    {#if authMode === 'login'}
      <LoginForm
        on:authenticated={handleAuthenticated}
        on:switchToRegister={() => {
          navigate('/app', 'register');
        }}
      />
    {:else}
      <RegisterForm
        on:authenticated={handleAuthenticated}
        on:switchToLogin={() => {
          navigate('/app', 'login');
        }}
      />
    {/if}
  {:else}
    <div class="flex h-screen w-full overflow-hidden bg-app-950 text-slate-100">
      <ServerList
        on:openSettings={() => {
          isSettingsOpen = true;
        }}
      />
      <ChannelList />
      <ChatWindow />
    </div>
    {#if isSettingsOpen}
      <SettingsModal
        isSubmitting={isSettingsSubmitting}
        on:close={() => {
          if (!isSettingsSubmitting) {
            isSettingsOpen = false;
          }
        }}
        on:logoutCurrent={handleLogout}
        on:logoutAll={handleLogoutAllSessions}
      />
    {/if}
  {/if}
{/if}

<ToastViewport />
