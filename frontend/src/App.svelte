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
  import { toApiAbsoluteUrl } from './lib/url';
  import { createGatewayEventHandler } from './app/gateway';
  import { servers } from './lib/stores/servers';
  import {
    activeChannel,
    activeDMConversation,
    activeServer,
    resolveStoredActiveView,
  } from './lib/stores/ui';
  import {
    connectGateway,
    disconnectGateway,
    joinGatewayChannel,
    joinGatewayDMConversation,
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
  } from './modules/chat/messages';
  import {
    ensureServerMembers,
    resetMembersState,
    updateServerMemberPresence,
  } from './modules/servers/members';
  import type { Server } from './types/gateway';
  import { LoginForm, RegisterForm, SettingsModal } from './modules/auth';
  import LandingPage from './modules/landing/LandingPage.svelte';
  import ServerList from './modules/servers/list';
  import ChannelList from './modules/channels';
  import ChatWindow from './modules/chat/window';
  import MemberSidebar from './modules/servers/members';
  import ToastViewport from './modules/shared/ToastViewport.svelte';
  import {
    addDMMessage,
    clearDMUnread,
    dmConversations,
    ensureDMConversations,
    ensureDMMessages,
    hydrateDMStateFromStorage,
    incrementDMUnread,
    hydrateFriendsStateFromStorage,
    loadFriendsData,
    resetDMState,
    resetFriendsState,
    softDeleteDMMessage,
    updateDMConversationPreview,
    updateDMMessage,
  } from './modules/dm';
  import { loadDMUICache, saveDMUICache } from './modules/dm/storage';
  import { DMWindow } from './modules/dm';
  import VoiceDock from './modules/voice/VoiceDock.svelte';
  import { leaveVoiceCall } from './modules/voice/store';
  import {
    applyVoiceMembersChanged,
    hydrateVoiceOccupants,
    resetVoiceOccupants,
  } from './modules/voice/occupancy';

  let unsubscribeGateway: (() => void) | null = null;
  let unsubscribeGatewayReconnect: (() => void) | null = null;
  const EMPTY_CHANNEL_MARKER = '__empty__';
  const READ_STATE_TTL_MS = 30_000;
  let lastReadMarkerByChannel: Record<string, string | undefined> = {};
  let readStateFetchedAtByChannel: Record<string, number | undefined> = {};
  let isBootstrapping = true;
  let isAuthenticated = false;
  let isSettingsOpen = false;
  let isSettingsSubmitting = false;
  let authMode: 'login' | 'register' = 'login';
  let routePath = '/';
  let uiPersistenceReady = false;
  const configuredAppUrl = import.meta.env.VITE_APP_URL?.replace(/\/$/, '') ?? '';

  function getDerivedAppUrl(): string {
    const { protocol, hostname, port, origin } = window.location;

    if (configuredAppUrl) {
      return configuredAppUrl;
    }

    if (hostname === 'localhost' || /^[\d.]+$/.test(hostname)) {
      return origin;
    }

    if (hostname.startsWith('app.')) {
      return origin;
    }

    const portSuffix = port ? `:${port}` : '';
    return `${protocol}//app.${hostname}${portSuffix}`;
  }

  function buildAppUrl(path: '/app', mode?: 'login' | 'register'): string {
    const search = mode ? `?mode=${mode}` : '';
    return `${getDerivedAppUrl()}${path}${search}`;
  }

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

  function navigate(
    path: '/' | '/app',
    mode?: 'login' | 'register',
    replaceState = false,
  ): void {
    if (path === '/app') {
      const targetUrl = buildAppUrl('/app', mode);
      const currentUrl = `${window.location.origin}${window.location.pathname}${window.location.search}`;

      if (targetUrl !== currentUrl && !window.location.origin.startsWith(getDerivedAppUrl())) {
        window.location[replaceState ? 'replace' : 'assign'](targetUrl);
        return;
      }
    }

    const search = path === '/app' && mode ? `?mode=${mode}` : '';
    const historyMethod = replaceState ? 'replaceState' : 'pushState';
    window.history[historyMethod]({}, '', `${path}${search}`);
    routePath = path;
    if (mode) {
      authMode = mode;
    }
  }

  function openAppAuth(mode: 'login' | 'register'): void {
    window.location.href = buildAppUrl('/app', mode);
  }

  function clearReadStateCache(): void {
    lastReadMarkerByChannel = {};
    readStateFetchedAtByChannel = {};
  }

  function tearDownGatewaySubscriptions(): void {
    unsubscribeGateway?.();
    unsubscribeGatewayReconnect?.();
    unsubscribeGateway = null;
    unsubscribeGatewayReconnect = null;
    disconnectGateway();
  }

  function applyUnauthenticatedState(): void {
    uiPersistenceReady = false;
    isAuthenticated = false;
    servers.set([]);
    activeServer.set(null);
    activeChannel.set(null);
    activeDMConversation.set(null);
    clearReadStateCache();
    resetChatState();
    resetDMState();
    resetFriendsState();
    resetMembersState();
    resetVoiceOccupants();
    tearDownGatewaySubscriptions();
    isSettingsOpen = false;
    isSettingsSubmitting = false;
    const currentPath = getCurrentPath();
    if (currentPath === '/') {
      authMode = 'login';
      navigate('/', undefined, true);
      return;
    }
    navigate('/app', 'login', true);
  }

  const handleGatewayEvent = createGatewayEventHandler({
    toApiAbsoluteUrl,
    pushToast,
    ensureServerMembers,
    updateServerMemberPresence,
    addMessage,
    incrementUnreadCount,
    softDeleteMessage,
    updateMessage,
    addDMMessage,
    updateDMMessage,
    softDeleteDMMessage,
    updateDMConversationPreview,
    incrementDMUnread,
    clearDMUnread,
    applyVoiceMembersChanged,
    getActiveChannelUuid: () => $activeChannel?.uuid ?? null,
    getActiveDMConversationUuid: () => $activeDMConversation?.uuid ?? null,
  });

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
    const dmConversationIds = $dmConversations.map((conversation) => conversation.uuid);
    for (const conversationUuid of dmConversationIds) {
      joinGatewayDMConversation(conversationUuid);
    }
    await loadFriendsData();
  }

  async function loadServers(): Promise<void> {
    const baseUrl = import.meta.env.VITE_API_URL;

    if (!baseUrl) {
      console.error('Missing VITE_API_URL in env.');
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
      hydrateVoiceOccupants(data);

      const restoredView = resolveStoredActiveView(data, loadDMUICache());
      activeServer.set(restoredView.activeServer);
      activeChannel.set(restoredView.activeChannel);
      if (!restoredView.isDMView) {
        activeDMConversation.set(null);
      }

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
      console.error('Failed to load servers:', error);
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
    uiPersistenceReady = false;
    hydrateDMStateFromStorage();
    hydrateFriendsStateFromStorage();
    await loadServers();
    uiPersistenceReady = true;
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

  $: if (isAuthenticated && !$activeServer) {
    ensureDMConversations();
    loadFriendsData();
  }

  $: if (uiPersistenceReady && isAuthenticated) {
    saveDMUICache({
      activeConversationUuid: $activeDMConversation?.uuid ?? null,
      activeServerUuid: $activeServer?.uuid ?? null,
      activeChannelUuid: $activeChannel?.uuid ?? null,
      isDMView: !$activeServer,
    });
  }

  $: if ($activeDMConversation?.uuid) {
    ensureDMMessages($activeDMConversation.uuid);
    joinGatewayDMConversation($activeDMConversation.uuid);
    clearDMUnread($activeDMConversation.uuid);
  }

  $: if ($activeServer?.uuid) {
    ensureServerMembers($activeServer.uuid);
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
    } else if (
      !latestMessageUuid &&
      lastReadMarkerByChannel[channelUuid] !== EMPTY_CHANNEL_MARKER
    ) {
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
    uiPersistenceReady = false;
    authMode = 'login';
    navigate('/app');
    await loadServers();
    uiPersistenceReady = true;
  }

  async function handleLogout(): Promise<void> {
    isSettingsSubmitting = true;
    const result = await logoutCurrentSession();
    isSettingsSubmitting = false;
    if (!result.ok) {
      pushToast({
        type: 'error',
        message: result.error ?? 'Failed to log out from this device.',
      });
      return;
    }
    await leaveVoiceCall();
    clearAuthTokens();
    pushToast({
      type: 'success',
      message: 'Logged out from this device.',
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
        message: result.error ?? 'Failed to log out from all devices.',
      });
      return;
    }
    await leaveVoiceCall();
    clearAuthTokens();
    pushToast({
      type: 'success',
      message: 'Logged out from all devices.',
    });
    applyUnauthenticatedState();
  }
</script>

{#if isBootstrapping}
  <div
    class="flex h-screen w-full items-center justify-center bg-surface-950 text-sm text-muted-300"
  >
    Loading...
  </div>
{:else if routePath === '/'}
  <LandingPage
    on:startLogin={() => {
      openAppAuth('login');
    }}
    on:startRegister={() => {
      openAppAuth('register');
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
  <div class="app-shell">
    <div class="ambient-blob left-[-10%] top-[-20%] h-[420px] w-[420px] bg-accent-500/25"></div>
    <div class="ambient-blob right-[-10%] top-[5%] h-[460px] w-[460px] bg-indigo-500/20"></div>
    <div class="ambient-blob bottom-[-20%] left-[35%] h-[380px] w-[380px] bg-cyan-500/15"></div>

    <div class="relative flex h-full w-full gap-2.5 text-slate-100 lg:gap-3">
      <ServerList
        on:openSettings={() => {
          isSettingsOpen = true;
        }}
      />
      <ChannelList />
      {#if $activeServer}
        <ChatWindow />
        <MemberSidebar />
      {:else}
        <DMWindow />
      {/if}
    </div>
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

<VoiceDock />
<ToastViewport />
