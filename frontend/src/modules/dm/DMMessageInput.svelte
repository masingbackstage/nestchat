<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Smile } from 'lucide-svelte';
  import { tick } from 'svelte';
  import { UNICODE_EMOJI_PICKER } from '../../lib/emoji';
  import { sendDMMessage } from '../../lib/socket';
  import { pushToast } from '../../lib/stores/toast';
  import type { DMConversation } from '../../types/gateway';

  export let conversation: DMConversation | null = null;

  let content = '';
  let textareaEl: HTMLTextAreaElement | null = null;
  let isEmojiPickerOpen = false;
  let emojiPickerRoot: HTMLDivElement | null = null;

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

  $: content, autoResizeTextarea();
</script>

<div class="border-t border-white/10 px-4 pb-4 pt-2">
  <div
    class="flex items-end gap-2 rounded-2xl border border-white/12 bg-white/5 px-2 py-2 focus-within:border-accent-400/60"
  >
    <textarea
      rows="1"
      bind:this={textareaEl}
      bind:value={content}
      on:keydown={handleKeydown}
      placeholder={conversation ? 'Message' : 'Select conversation'}
      disabled={!conversation}
      class="max-h-[260px] min-h-[38px] flex-1 resize-none bg-transparent px-1.5 py-2 text-sm text-slate-100 outline-none placeholder:text-muted-400 disabled:cursor-not-allowed disabled:opacity-60"
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
      disabled={!conversation || content.trim().length === 0}
      class="inline-flex h-9 shrink-0 items-center self-end rounded-xl bg-accent-500 px-3 text-sm font-medium text-white transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-surface-800"
    >
      Send
    </button>
  </div>
</div>
