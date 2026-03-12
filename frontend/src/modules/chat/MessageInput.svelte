<script lang="ts">
  import { onDestroy, tick } from 'svelte';
  import { PlusCircle, Smile } from 'lucide-svelte';
  import { UNICODE_EMOJI_PICKER } from '../../lib/emoji';
  import { activeChannel } from '../../lib/stores/ui';
  import { sendChatMessage } from '../../lib/socket';
  import { addPendingMessage, createClientMessageId, wasClientIdDelivered } from './messages.store';

  const DRAFTS_STORAGE_KEY = 'chat_channel_drafts_v1';
  const PENDING_MESSAGE_DELAY_MS = 250;

  let content = '';
  let localError = '';
  let currentDraftChannelUuid: string | null = null;
  let draftsByChannel: Record<string, string> = {};
  let textareaEl: HTMLTextAreaElement | null = null;
  let isEmojiPickerOpen = false;
  let emojiPickerRoot: HTMLDivElement | null = null;
  const MIN_TEXTAREA_HEIGHT_PX = 38;
  const MAX_TEXTAREA_HEIGHT_PX = 420;

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

  async function submitMessage(): Promise<void> {
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
    await tick();
    autoResizeTextarea();
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  }

  function autoResizeTextarea(): void {
    if (!textareaEl) {
      return;
    }

    textareaEl.style.height = `${MIN_TEXTAREA_HEIGHT_PX}px`;
    const nextHeight = Math.min(textareaEl.scrollHeight, MAX_TEXTAREA_HEIGHT_PX);
    textareaEl.style.height = `${Math.max(MIN_TEXTAREA_HEIGHT_PX, nextHeight)}px`;
    textareaEl.style.overflowY =
      textareaEl.scrollHeight > MAX_TEXTAREA_HEIGHT_PX ? 'auto' : 'hidden';
  }

  function insertEmoji(emoji: string): void {
    if (!textareaEl || !$activeChannel) {
      return;
    }
    const start = textareaEl.selectionStart ?? content.length;
    const end = textareaEl.selectionEnd ?? content.length;
    const next = `${content.slice(0, start)}${emoji}${content.slice(end)}`;
    content = next;
    isEmojiPickerOpen = false;

    tick().then(() => {
      if (!textareaEl) {
        return;
      }
      const caret = start + emoji.length;
      textareaEl.focus();
      textareaEl.setSelectionRange(caret, caret);
      autoResizeTextarea();
    });
  }

  function handleDocumentPointerDown(event: PointerEvent): void {
    if (!isEmojiPickerOpen || !emojiPickerRoot) {
      return;
    }
    const target = event.target;
    if (!(target instanceof Node)) {
      return;
    }
    if (emojiPickerRoot.contains(target)) {
      return;
    }
    isEmojiPickerOpen = false;
  }

  document.addEventListener('pointerdown', handleDocumentPointerDown, true);
  onDestroy(() => {
    document.removeEventListener('pointerdown', handleDocumentPointerDown, true);
  });

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

  $: content, autoResizeTextarea();
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
      bind:this={textareaEl}
      bind:value={content}
      on:input={autoResizeTextarea}
      on:keydown={handleKeydown}
      placeholder={$activeChannel ? `Message #${$activeChannel.name}` : 'Select a channel'}
      disabled={!$activeChannel}
      class="max-h-[420px] min-h-[38px] flex-1 resize-none bg-transparent px-1.5 py-2 text-sm text-slate-100 outline-none placeholder:text-muted-400 disabled:cursor-not-allowed disabled:opacity-60"
    ></textarea>
    <div class="relative" bind:this={emojiPickerRoot}>
      <button
        type="button"
        class={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-muted-300 transition hover:bg-white/10 hover:text-slate-100 ${
          isEmojiPickerOpen ? 'bg-white/10 text-slate-100' : ''
        }`}
        aria-label="Emoji"
        on:click={() => {
          isEmojiPickerOpen = !isEmojiPickerOpen;
        }}
      >
        <Smile class="h-5 w-5" />
      </button>
      {#if isEmojiPickerOpen}
        <div
          class="absolute bottom-full right-0 z-30 mb-2 w-[280px] rounded-lg border border-white/15 bg-surface-900 p-2 shadow-lg"
        >
          <div class="app-scrollbar grid max-h-48 grid-cols-8 gap-1 overflow-auto pr-1">
            {#each UNICODE_EMOJI_PICKER as emoji (emoji)}
              <button
                type="button"
                class="rounded px-1.5 py-1 text-base transition hover:bg-white/10"
                on:click={() => insertEmoji(emoji)}
                title={emoji}
                aria-label={emoji}
              >
                {emoji}
              </button>
            {/each}
          </div>
        </div>
      {/if}
    </div>
    <button
      type="button"
      on:click={submitMessage}
      disabled={!$activeChannel || content.trim().length === 0}
      class="inline-flex h-9 shrink-0 items-center self-end rounded-xl bg-accent-500 px-3 text-sm font-medium text-white transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-surface-800"
    >
      Send
    </button>
  </div>
</div>
