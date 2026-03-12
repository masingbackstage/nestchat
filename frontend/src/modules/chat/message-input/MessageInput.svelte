<script lang="ts">
  import { tick } from 'svelte';
  import { PlusCircle } from 'lucide-svelte';
  import { UNICODE_EMOJI_PICKER } from '../../../lib/emoji';
  import { activeChannel } from '../../../lib/stores/ui';
  import { sendChatMessage } from '../../../lib/socket';
  import {
    addPendingMessage,
    createClientMessageId,
    wasClientIdDelivered,
  } from '../messages';
  import { loadDraftsFromStorage, saveDraftsToStorage, setDraftValue } from './drafts';
  import EmojiPicker from './EmojiPicker.svelte';

  const PENDING_MESSAGE_DELAY_MS = 250;
  const MIN_TEXTAREA_HEIGHT_PX = 38;
  const MAX_TEXTAREA_HEIGHT_PX = 420;

  let content = '';
  let localError = '';
  let currentDraftChannelUuid: string | null = null;
  let draftsByChannel: Record<string, string> = loadDraftsFromStorage();
  let textareaEl: HTMLTextAreaElement | null = null;

  function persistDraft(channelUuid: string, value: string): void {
    draftsByChannel = setDraftValue(draftsByChannel, channelUuid, value);
    saveDraftsToStorage(draftsByChannel);
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
    persistDraft($activeChannel.uuid, '');
    await tick();
    autoResizeTextarea();
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void submitMessage();
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

  $: activeUuid = $activeChannel?.uuid ?? null;
  $: if (activeUuid !== currentDraftChannelUuid) {
    if (currentDraftChannelUuid) {
      persistDraft(currentDraftChannelUuid, content);
    }
    currentDraftChannelUuid = activeUuid;
    content = activeUuid ? (draftsByChannel[activeUuid] ?? '') : '';
  }

  $: if (currentDraftChannelUuid) {
    persistDraft(currentDraftChannelUuid, content);
  }

  $: if (content !== undefined) {
    autoResizeTextarea();
  }
</script>

<div class="message-input-shell">
  {#if localError}
    <p class="message-input-error">{localError}</p>
  {/if}

  <div class="message-input-form">
    <button type="button" class="message-input-attachment-button" aria-label="Add attachment">
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
      class="message-input-textarea"
    ></textarea>
    <EmojiPicker emojis={UNICODE_EMOJI_PICKER} onSelect={insertEmoji} />
    <button
      type="button"
      on:click={() => void submitMessage()}
      disabled={!$activeChannel || content.trim().length === 0}
      class="message-input-send-button"
    >
      Send
    </button>
  </div>
</div>

<style>
  .message-input-shell {
    @apply border-t border-white/10 px-4 pb-4 pt-2;
  }

  .message-input-error {
    @apply mb-2 text-xs text-red-300;
  }

  .message-input-form {
    @apply flex items-end gap-2 rounded-2xl border border-white/10 bg-white/5 px-2 py-2 focus-within:border-accent-400/60;
  }

  .message-input-attachment-button {
    @apply flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-muted-300 transition hover:bg-white/10 hover:text-slate-100;
  }

  .message-input-textarea {
    @apply max-h-[420px] min-h-[38px] flex-1 resize-none bg-transparent px-1.5 py-2 text-sm text-slate-100 outline-none placeholder:text-muted-400 disabled:cursor-not-allowed disabled:opacity-60;
  }

  .message-input-send-button {
    @apply inline-flex h-9 shrink-0 items-center self-end rounded-xl bg-accent-500 px-3 text-sm font-medium text-white transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-surface-800;
  }
</style>
