<script lang="ts">
  import { tick } from 'svelte';
  import { sendDMMessage } from '../../../lib/socket';
  import { pushToast } from '../../../lib/stores/toast';
  import type { DMConversation } from '../../../types/gateway';
  import { UNICODE_EMOJI_PICKER } from '../../../lib/emoji';
  import EmojiPicker from '../../chat/message-input/EmojiPicker.svelte';

  export let conversation: DMConversation | null = null;

  let content = '';
  let textareaEl: HTMLTextAreaElement | null = null;

  function autoResizeTextarea(): void {
    if (!textareaEl) {
      return;
    }
    textareaEl.style.height = '38px';
    const maxHeight = 260;
    const nextHeight = Math.min(textareaEl.scrollHeight, maxHeight);
    textareaEl.style.height = `${Math.max(38, nextHeight)}px`;
    textareaEl.style.overflowY = textareaEl.scrollHeight > maxHeight ? 'auto' : 'hidden';
  }

  async function submitMessage(): Promise<void> {
    const trimmed = content.trim();
    if (!trimmed || !conversation) {
      return;
    }

    const sent = sendDMMessage(conversation.uuid, trimmed);
    if (!sent) {
      pushToast({ type: 'error', message: 'Gateway connection is unavailable.' });
      return;
    }

    content = '';
    await tick();
    autoResizeTextarea();
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void submitMessage();
    }
  }

  function insertEmoji(emoji: string): void {
    if (!textareaEl) {
      return;
    }

    const start = textareaEl.selectionStart ?? content.length;
    const end = textareaEl.selectionEnd ?? content.length;
    content = `${content.slice(0, start)}${emoji}${content.slice(end)}`;
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

  $: if (content !== undefined) {
    autoResizeTextarea();
  }
</script>

<div class="dm-message-input-shell">
  <div class="dm-message-input-form">
    <textarea
      rows="1"
      bind:this={textareaEl}
      bind:value={content}
      on:keydown={handleKeydown}
      placeholder={conversation ? 'Message' : 'Select conversation'}
      disabled={!conversation}
      class="dm-message-input-textarea"
    ></textarea>
    <EmojiPicker emojis={UNICODE_EMOJI_PICKER} onSelect={insertEmoji} />
    <button
      type="button"
      on:click={submitMessage}
      disabled={!conversation || content.trim().length === 0}
      class="dm-message-input-send-button"
    >
      Send
    </button>
  </div>
</div>

<style>
  .dm-message-input-shell {
    @apply border-t border-white/10 px-4 pb-4 pt-2;
  }

  .dm-message-input-form {
    @apply flex items-end gap-2 rounded-2xl border border-white/10 bg-white/5 px-2 py-2 focus-within:border-accent-400/60;
  }

  .dm-message-input-textarea {
    @apply max-h-[260px] min-h-[38px] flex-1 resize-none bg-transparent px-1.5 py-2 text-sm text-slate-100 outline-none placeholder:text-muted-400 disabled:cursor-not-allowed disabled:opacity-60;
  }

  .dm-message-input-send-button {
    @apply inline-flex h-9 shrink-0 items-center self-end rounded-xl bg-accent-500 px-3 text-sm font-medium text-white transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-surface-800;
  }
</style>
