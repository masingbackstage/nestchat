<script lang="ts">
  import { PhoneOff, Mic, MicOff, Video, VideoOff, MonitorUp, MonitorOff } from 'lucide-svelte';
  import {
    voiceState,
    leaveVoiceCall,
    toggleMute,
    toggleCamera,
    toggleScreenShare,
    reconnectVoiceCall,
  } from './store';

  export let isIntegrated = false;
  export let isMini = false;

  $: statusLabel =
    $voiceState.status === 'connecting'
      ? 'Connecting'
      : $voiceState.status === 'connected'
        ? 'Connected'
        : $voiceState.status === 'error'
          ? 'Error'
          : 'Idle';
</script>

{#if $voiceState.status !== 'idle'}
  {#if isMini}
    <div class="voice-dock-mini">
      <div class="flex w-full flex-col px-4 py-3 gap-3">
        <div class="flex items-center justify-between gap-2">
          <div class="min-w-0 flex-1">
            <p class="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
              Voice Connected
            </p>
            <p
              class="truncate text-sm font-medium text-slate-100 mt-0.5"
              title={$voiceState.channelName}
            >
              {$voiceState.channelName ?? 'Voice'}
            </p>
          </div>
          <button
            type="button"
            class="btn-mini btn-danger w-9 shrink-0"
            on:click={() => void leaveVoiceCall()}
            title="Disconnect"
          >
            <PhoneOff class="h-4 w-4" />
          </button>
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            class="btn-mini flex-1"
            class:is-active={$voiceState.cameraEnabled}
            on:click={() => void toggleCamera()}
            disabled={$voiceState.status !== 'connected'}
            title={$voiceState.cameraEnabled ? 'Turn off camera' : 'Turn on camera'}
          >
            {#if $voiceState.cameraEnabled}<Video class="h-4 w-4" />{:else}<VideoOff
                class="h-4 w-4"
              />{/if}
          </button>

          <button
            type="button"
            class="btn-mini flex-1"
            class:is-active={$voiceState.screenShareEnabled}
            on:click={() => void toggleScreenShare()}
            disabled={$voiceState.status !== 'connected'}
            title={$voiceState.screenShareEnabled ? 'Stop sharing screen' : 'Share screen'}
          >
            {#if $voiceState.screenShareEnabled}<MonitorUp class="h-4 w-4" />{:else}<MonitorOff
                class="h-4 w-4"
              />{/if}
          </button>

          <button
            type="button"
            class="btn-mini flex-1"
            class:is-muted={$voiceState.muted}
            on:click={() => void toggleMute()}
            disabled={$voiceState.status !== 'connected'}
            title={$voiceState.muted ? 'Unmute' : 'Mute'}
          >
            {#if $voiceState.muted}<MicOff class="h-4 w-4" />{:else}<Mic class="h-4 w-4" />{/if}
          </button>
        </div>
      </div>
    </div>
  {:else}
    <div
      class="voice-dock"
      class:dock-floating={!isIntegrated}
      class:dock-integrated={isIntegrated}
    >
      {#if !isIntegrated}
        <div class="voice-copy">
          <p class="text-xs text-emerald-400 font-medium tracking-wide">Voice Connected</p>
          <p class="text-sm font-semibold text-slate-100 mt-0.5">{statusLabel}</p>

          {#if $voiceState.channelName}
            <p class="text-xs text-muted-400 truncate mt-0.5">{$voiceState.channelName}</p>
          {/if}

          {#if $voiceState.error}
            <p class="text-xs text-red-400 mt-1">{$voiceState.error}</p>
          {/if}
        </div>
      {/if}

      <div class="controls-row">
        {#if $voiceState.status === 'error'}
          <button type="button" class="btn-retry" on:click={() => void reconnectVoiceCall()}>
            Retry
          </button>
        {/if}

        <button
          type="button"
          class="btn-action"
          class:is-active={$voiceState.cameraEnabled}
          on:click={() => void toggleCamera()}
          disabled={$voiceState.status !== 'connected'}
          title={$voiceState.cameraEnabled ? 'Turn off camera' : 'Turn on camera'}
        >
          {#if $voiceState.cameraEnabled}<Video class="h-5 w-5" />{:else}<VideoOff
              class="h-5 w-5"
            />{/if}
        </button>

        <button
          type="button"
          class="btn-action"
          class:is-active={$voiceState.screenShareEnabled}
          on:click={() => void toggleScreenShare()}
          disabled={$voiceState.status !== 'connected'}
          title={$voiceState.screenShareEnabled ? 'Stop sharing screen' : 'Share screen'}
        >
          {#if $voiceState.screenShareEnabled}<MonitorUp class="h-5 w-5" />{:else}<MonitorOff
              class="h-5 w-5"
            />{/if}
        </button>

        <button
          type="button"
          class="btn-action"
          class:is-muted={$voiceState.muted}
          on:click={() => void toggleMute()}
          disabled={$voiceState.status !== 'connected'}
          title={$voiceState.muted ? 'Unmute' : 'Mute'}
        >
          {#if $voiceState.muted}<MicOff class="h-5 w-5" />{:else}<Mic class="h-5 w-5" />{/if}
        </button>

        <div class="divider"></div>

        <button
          type="button"
          class="btn-action btn-danger"
          on:click={() => void leaveVoiceCall()}
          title="Disconnect"
        >
          <PhoneOff class="h-5 w-5" />
        </button>
      </div>
    </div>
  {/if}
{/if}

<style>
  .voice-dock-mini {
    @apply w-full bg-surface-900/60 transition-all duration-300;
  }

  .btn-mini {
    @apply flex h-9 items-center justify-center rounded-lg bg-white/5 text-slate-300 hover:bg-white/10 hover:text-slate-100 transition border border-transparent;
  }

  .voice-dock {
    @apply flex items-center bg-surface-900/60 backdrop-blur-xl border border-white/10 shadow-2xl transition-all duration-300;
  }

  .dock-floating {
    @apply fixed bottom-5 right-6 z-50 gap-5 rounded-2xl px-5 py-4;
    width: min(480px, calc(100vw - 2rem));
  }

  .dock-integrated {
    @apply rounded-full px-8 py-3;
  }

  .voice-copy {
    @apply min-w-0 flex-1;
  }

  .controls-row {
    @apply flex items-center justify-center gap-3;
  }

  .divider {
    @apply w-px h-8 bg-white/10 mx-1;
  }

  .btn-retry {
    @apply rounded-lg border border-white/15 px-3 py-2 text-sm text-slate-100 hover:bg-white/10 transition;
  }

  .btn-action {
    @apply flex h-12 w-12 items-center justify-center rounded-full bg-white/10 text-slate-200 hover:bg-white/20 transition-all duration-200 border border-transparent shadow-sm;
  }

  .is-active {
    @apply bg-emerald-500/20 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/30;
  }

  .is-muted {
    @apply bg-white/5 text-muted-400 hover:bg-white/10;
  }

  .btn-danger {
    @apply bg-red-500/90 text-white shadow-md hover:bg-red-400 border-red-400/50;
  }

  .btn-action.btn-danger {
    @apply hover:scale-105;
  }

  .btn-action:disabled,
  .btn-mini:disabled {
    @apply opacity-50 cursor-not-allowed hover:bg-white/10 hover:scale-100;
  }
</style>
