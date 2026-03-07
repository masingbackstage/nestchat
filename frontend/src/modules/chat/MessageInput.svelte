<script lang="ts">
  import { PlusCircle, Smile } from 'lucide-svelte';
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
      localError = 'Gateway connection is unavailable.';
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

<div class="border-t border-white/10 px-4 pb-4 pt-2">
  {#if localError}
    <p class="mb-2 text-xs text-red-300">{localError}</p>
  {/if}

  <div
    class="flex items-end gap-2 rounded-2xl border border-white/12 bg-white/5 px-2 py-2 focus-within:border-accent-400/60"
  >
    <button
      type="button"
      class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-muted-300 transition hover:bg-white/10 hover:text-slate-100"
      aria-label="Add attachment"
    >
      <PlusCircle class="h-5 w-5" />
    </button>
    <textarea
      rows="1"
      bind:value={content}
      on:keydown={handleKeydown}
      placeholder={$activeChannel ? `Message #${$activeChannel.name}` : 'Select a channel'}
      disabled={!$activeChannel}
      class="max-h-44 min-h-[38px] flex-1 resize-y bg-transparent px-1.5 py-2 text-sm text-slate-100 outline-none placeholder:text-muted-400 disabled:cursor-not-allowed disabled:opacity-60"
    ></textarea>
    <button
      type="button"
      class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-muted-300 transition hover:bg-white/10 hover:text-slate-100"
      aria-label="Emoji"
    >
      <Smile class="h-5 w-5" />
    </button>
    <button
      type="button"
      on:click={submitMessage}
      disabled={!$activeChannel || content.trim().length === 0}
      class="rounded-xl bg-accent-500 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-surface-800"
    >
      Send
    </button>
  </div>
</div>
