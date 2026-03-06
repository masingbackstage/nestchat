<script lang="ts">
  import { activeChannel } from '../../lib/stores/ui';
  import { sendChatMessage } from '../../lib/socket';

  let content = '';
  let localError = '';

  function submitMessage(): void {
    const trimmed = content.trim();
    if (!trimmed || !$activeChannel) {
      return;
    }

    const sent = sendChatMessage($activeChannel.uuid, trimmed);
    if (!sent) {
      localError = 'Brak połączenia z gateway.';
      return;
    }

    content = '';
    localError = '';
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  }
</script>

<div class="border-t border-slate-700 p-4">
  {#if localError}
    <p class="mb-2 text-xs text-red-400">{localError}</p>
  {/if}

  <textarea
    rows="1"
    bind:value={content}
    on:keydown={handleKeydown}
    placeholder={$activeChannel ? `Napisz na #${$activeChannel.name}` : 'Wybierz kanał'}
    disabled={!$activeChannel}
    class="max-h-48 min-h-[44px] w-full resize-y rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
  ></textarea>

  <div class="mt-2 flex justify-end">
    <button
      type="button"
      on:click={submitMessage}
      disabled={!$activeChannel || content.trim().length === 0}
      class="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-700"
    >
      Wyślij
    </button>
  </div>
</div>
