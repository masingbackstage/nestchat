<script lang="ts">
  import { MicOff, Maximize } from 'lucide-svelte';
  import { Track } from 'livekit-client';
  import { activeChannel } from '../../lib/stores/ui';
  import { voiceOccupantsByChannel } from './occupancy';
  import { getCurrentUserUuid } from '../../lib/auth';
  import {
    voiceState,
    remoteVideoTracks,
    localVideoStream,
    localScreenStream,
    type RemoteVideoEntry,
  } from './store';
  import type { VoiceOccupant } from '../../types/gateway';
  import VoiceDock from './VoiceDock.svelte';

  $: channelUuid = $activeChannel?.uuid;
  $: occupants = channelUuid ? ($voiceOccupantsByChannel[channelUuid] ?? []) : [];

  type VideoTile = {
    key: string;
    label: string;
    stream: MediaStream | null;
    isLocal: boolean;
    isMirrored: boolean;
    isScreenShare: boolean;
    avatarUrl: string | null;
    initials: string;
    isSpeaking: boolean;
    isMuted: boolean;
  };

  $: tiles = buildTiles(
    occupants,
    $remoteVideoTracks,
    $localVideoStream,
    $localScreenStream,
    $voiceState.cameraEnabled,
    $voiceState.screenShareEnabled,
  );

  $: gridClass = computeGridClass(
    tiles.length,
    tiles.some((t) => t.isScreenShare),
  );

  function getInitials(name: string): string {
    return name.slice(0, 2).toUpperCase();
  }

  function ignorePlaybackError(): void {
    // Autoplay/fullscreen can be blocked by the browser; the UI should stay usable.
  }

  function buildTiles(
    occupantsList: VoiceOccupant[],
    remote: RemoteVideoEntry[],
    localCam: MediaStream | null,
    localScreen: MediaStream | null,
    camOn: boolean,
    screenOn: boolean,
  ): VideoTile[] {
    const result: VideoTile[] = [];
    const selfUuid = getCurrentUserUuid();

    for (const occupant of occupantsList) {
      const isSelf = occupant.user_uuid === selfUuid;
      const name = occupant.display_name ?? 'Unknown user';
      const avatarUrl = occupant.avatar_url ?? null;
      const initials = getInitials(name);
      const isSpeaking = occupant.is_speaking ?? false;
      const isMuted = occupant.is_muted ?? false;

      // Screen share tile
      if (isSelf && localScreen && screenOn) {
        result.push({
          key: `screen-${occupant.user_uuid}`,
          label: `${name}'s screen`,
          stream: localScreen,
          isLocal: true,
          isMirrored: false,
          isScreenShare: true,
          avatarUrl: null,
          initials: '',
          isSpeaking: false,
          isMuted: false,
        });
      } else if (!isSelf) {
        const remoteScreen = remote.find(
          (t) =>
            t.participantIdentity === occupant.user_uuid && t.source === Track.Source.ScreenShare,
        );
        if (remoteScreen) {
          result.push({
            key: `screen-${occupant.user_uuid}`,
            label: `${name}'s screen`,
            stream: remoteScreen.mediaStream,
            isLocal: false,
            isMirrored: false,
            isScreenShare: true,
            avatarUrl: null,
            initials: '',
            isSpeaking: false,
            isMuted: false,
          });
        }
      }

      // Camera / Avatar tile
      let stream: MediaStream | null = null;
      let isMirrored = false;

      if (isSelf && localCam && camOn) {
        stream = localCam;
        isMirrored = false;
      } else if (!isSelf) {
        const remoteCam = remote.find(
          (t) => t.participantIdentity === occupant.user_uuid && t.source === Track.Source.Camera,
        );
        if (remoteCam) {
          stream = remoteCam.mediaStream;
        }
      }

      result.push({
        key: `main-${occupant.user_uuid}`,
        label: name,
        stream,
        isLocal: isSelf,
        isMirrored,
        isScreenShare: false,
        avatarUrl,
        initials,
        isSpeaking,
        isMuted,
      });
    }

    // Sort screen shares first
    result.sort((a, b) => {
      if (a.isScreenShare && !b.isScreenShare) {
        return -1;
      }
      if (!a.isScreenShare && b.isScreenShare) {
        return 1;
      }
      return 0;
    });

    return result;
  }

  function computeGridClass(count: number, hasScreenShare: boolean): string {
    if (count <= 1) {
      return 'grid-cols-1';
    }
    if (count === 2 && !hasScreenShare) {
      return 'grid-cols-2';
    }
    if (count <= 4) {
      return 'grid-cols-2';
    }
    if (count <= 9) {
      return 'grid-cols-3';
    }
    return 'grid-cols-4';
  }

  function attachStream(
    videoEl: HTMLVideoElement,
    stream: MediaStream | null,
  ): { destroy: () => void; update: (newStream: MediaStream | null) => void } {
    videoEl.srcObject = stream;
    if (stream) {
      void videoEl.play().catch(ignorePlaybackError);
    }

    return {
      update(newStream) {
        if (videoEl.srcObject !== newStream) {
          videoEl.srcObject = newStream;
          if (newStream) {
            void videoEl.play().catch(ignorePlaybackError);
          }
        }
      },
      destroy() {
        videoEl.srcObject = null;
      },
    };
  }
  function toggleFullscreen(event: MouseEvent): void {
    const tile = (event.currentTarget as HTMLElement).closest('.video-tile');
    if (!tile) {
      return;
    }

    if (!document.fullscreenElement) {
      void tile.requestFullscreen?.().catch(ignorePlaybackError);
    } else {
      void document.exitFullscreen?.().catch(ignorePlaybackError);
    }
  }
</script>

<main class="voice-grid-window">
  <div class="voice-grid-header">
    <div class="voice-grid-title">
      <span class="text-muted-400 mr-2">#</span>{$activeChannel?.name ?? 'Voice Channel'}
    </div>
  </div>

  <div class="voice-grid-content">
    {#if tiles.length > 0}
      <div class="video-grid {gridClass}">
        {#each tiles as tile (tile.key)}
          <div
            class="video-tile group"
            class:video-tile-screen={tile.isScreenShare}
            class:video-tile-speaking={tile.isSpeaking}
          >
            {#if tile.stream}
              <video
                autoplay
                playsinline
                muted={tile.isLocal}
                class="video-element"
                class:video-element-contain={tile.isScreenShare}
                class:video-mirrored={tile.isMirrored}
                use:attachStream={tile.stream}
              ></video>
              <button
                type="button"
                class="fullscreen-btn"
                on:click={(e) => toggleFullscreen(e)}
                title="Pełny ekran"
              >
                <Maximize class="h-4 w-4" />
              </button>
            {:else}
              <div class="avatar-container">
                {#if tile.avatarUrl}
                  <img src={tile.avatarUrl} alt={tile.label} class="avatar-img" />
                {:else}
                  <div class="avatar-fallback">{tile.initials}</div>
                {/if}
              </div>
            {/if}

            <div class="video-tile-label">
              <span class="truncate max-w-[90%]">{tile.label}</span>
              {#if tile.isMuted}
                <div class="text-red-400">
                  <MicOff class="h-3 w-3" />
                </div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="empty-state">
        <p class="text-slate-200">No one is in this channel right now.</p>
        {#if $voiceState.status !== 'connected'}
          <p class="text-xs text-muted-400 mt-2">Join the call to see occupants.</p>
        {/if}
      </div>
    {/if}

    <div class="absolute bottom-6 inset-x-0 z-20 flex justify-center pointer-events-none">
      <div class="pointer-events-auto">
        <VoiceDock isIntegrated={true} />
      </div>
    </div>
  </div>
</main>

<style>
  .voice-grid-window {
    @apply relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden rounded-panel border border-white/5 bg-surface-900/40 backdrop-blur-xl;
  }

  .voice-grid-header {
    @apply flex h-14 shrink-0 items-center border-b border-white/5 px-4 shadow-sm;
  }

  .voice-grid-title {
    @apply flex items-center text-lg font-semibold text-slate-100;
  }

  .voice-grid-content {
    @apply relative flex min-w-0 flex-1 flex-col overflow-hidden p-4;
  }

  .video-grid {
    @apply grid gap-4 h-full w-full;
  }

  .grid-cols-1 {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr;
  }
  .grid-cols-2 {
    grid-template-columns: repeat(2, 1fr);
    grid-auto-rows: 1fr;
  }
  .grid-cols-3 {
    grid-template-columns: repeat(3, 1fr);
    grid-auto-rows: 1fr;
  }
  .grid-cols-4 {
    grid-template-columns: repeat(4, 1fr);
    grid-auto-rows: 1fr;
  }

  .video-tile {
    @apply relative flex items-center justify-center overflow-hidden rounded-xl bg-black/40 border border-white/5 transition-all duration-200;
  }

  .video-tile-screen {
    grid-column: 1 / -1;
    grid-row: span 2;
  }

  .video-tile-speaking {
    @apply ring-2 ring-emerald-500/80 shadow-[0_0_15px_rgba(16,185,129,0.3)];
  }

  .video-element {
    @apply h-full w-full object-cover;
  }

  /* Make sure video keeps aspect ratio when fullscreened to not crop top/bottom */
  .video-tile:fullscreen .video-element {
    object-fit: contain !important;
  }

  .video-element-contain {
    object-fit: contain !important;
    @apply bg-black/80;
  }

  .fullscreen-btn {
    @apply absolute top-3 right-3 z-30 flex h-8 w-8 items-center justify-center rounded-lg bg-black/50 text-white opacity-0 backdrop-blur-sm transition-all hover:bg-black/70 group-hover:opacity-100 border border-white/10;
  }

  .video-mirrored {
    transform: scaleX(-1);
  }

  .avatar-container {
    @apply flex h-24 w-24 items-center justify-center rounded-full bg-white/10 overflow-hidden shadow-lg border border-white/10;
  }

  .avatar-img {
    @apply h-full w-full object-cover;
  }

  .avatar-fallback {
    @apply flex h-full w-full items-center justify-center text-3xl font-semibold text-slate-200;
  }

  .video-tile-label {
    @apply absolute bottom-3 left-3 flex items-center gap-2 rounded-lg bg-black/60 backdrop-blur-md px-2.5 py-1 text-xs font-medium text-white shadow-sm border border-white/10;
  }

  .empty-state {
    @apply flex h-full flex-col items-center justify-center text-center;
  }
</style>
