<script lang="ts">
  import { PhoneOff, Mic, MicOff } from 'lucide-svelte';
  import { voiceState, leaveVoiceCall, toggleMute, reconnectVoiceCall } from './store';

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
  <div class="voice-dock glass-panel">
    <div class="voice-copy">
      <p class="text-xs text-muted-300">Voice</p>
      <p class="text-sm text-slate-100">{statusLabel}</p>

      {#if $voiceState.channelName}
        <p class="text-xs text-muted-400 truncate">{$voiceState.channelName}</p>
      {/if}

      {#if $voiceState.error}
        <p class="text-xs text-red-300">{$voiceState.error}</p>
      {/if}
    </div>

    <div class="flex items-center gap-2">
      {#if $voiceState.status === 'error'}
        <button type="button" class="btn" on:click={() => void reconnectVoiceCall()}>
          Retry
        </button>
      {/if}

      <button
        type="button"
        class="btn"
        on:click={() => void toggleMute()}
        disabled={$voiceState.status !== 'connected'}
      >
        {#if $voiceState.muted}<MicOff class="h-4 w-4" />{:else}<Mic class="h-4 w-4" />{/if}
      </button>

      <button type="button" class="btn btn-danger" on:click={() => void leaveVoiceCall()}>
        <PhoneOff class="h-4 w-4" />
      </button>
    </div>
  </div>
{/if}

<style>
  .voice-dock {
    @apply fixed bottom-4 right-6 z-50 flex items-center gap-4 rounded-xl px-4 py-3;
    width: min(420px, calc(100vw - 2rem));
  }
  .voice-copy {
    @apply min-w-0 flex-1;
  }
  .btn {
    @apply rounded-lg border border-white/15 px-2 py-2 text-slate-100 hover:bg-white/10;
  }
  .btn-danger {
    @apply border-red-500/40 text-red-200 hover:bg-red-500/20;
  }
</style>
