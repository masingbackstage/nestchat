<script lang="ts">
  import { activeChannel } from '../../lib/stores/ui';
  import { sendChatMessage } from '../../lib/socket';
  import { addPendingMessage, createClientMessageId, wasClientIdDelivered } from './messages.store';

  const DRAFTS_STORAGE_KEY = 'chat_channel_drafts_v1';
  const PENDING_MESSAGE_DELAY_MS = 250;

  let content = '';
  let localError = '';
  let currentDraftChannelUuid: string | null = null;
  let draftsByChannel: Record<string, string> = {};

  function loadDraftsFromStorage(): void {
    try {
      const raw = localStorage.getItem(DRAFTS_STORAGE_KEY);
      if (!raw) {
        draftsByChannel = {};
        return;
      }
      const parsed = JSON.parse(raw) as Record<string, string>;
      draftsByChannel = parsed ?? {};
    } catch {
      draftsByChannel = {};
    }
  }

  function saveDraftsToStorage(): void {
    localStorage.setItem(DRAFTS_STORAGE_KEY, JSON.stringify(draftsByChannel));
  }

  function setDraft(channelUuid: string, value: string): void {
    if (value.trim().length === 0) {
      draftsByChannel = Object.fromEntries(
        Object.entries(draftsByChannel).filter(([uuid]) => uuid !== channelUuid),
      );
    } else {
      draftsByChannel[channelUuid] = value;
    }
    saveDraftsToStorage();
  }

  function submitMessage(): void {
    const trimmed = content.trim();
    if (!trimmed || !$activeChannel) {
      return;
    }

    const channelUuid = $activeChannel.uuid;
    const clientId = createClientMessageId();
    const sent = sendChatMessage($activeChannel.uuid, trimmed, clientId);
    if (!sent) {
      localError = 'Brak połączenia z gateway.';
      return;
    }

    setTimeout(() => {
      if (wasClientIdDelivered(channelUuid, clientId)) {
        return;
      }
      addPendingMessage(channelUuid, trimmed, clientId);
    }, PENDING_MESSAGE_DELAY_MS);

    content = '';
    localError = '';
    setDraft($activeChannel.uuid, '');
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  }

  loadDraftsFromStorage();

  $: activeUuid = $activeChannel?.uuid ?? null;
  $: if (activeUuid !== currentDraftChannelUuid) {
    if (currentDraftChannelUuid) {
      setDraft(currentDraftChannelUuid, content);
    }
    currentDraftChannelUuid = activeUuid;
    content = activeUuid ? (draftsByChannel[activeUuid] ?? '') : '';
  }

  $: if (currentDraftChannelUuid) {
    setDraft(currentDraftChannelUuid, content);
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
