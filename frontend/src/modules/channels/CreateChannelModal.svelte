<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { fade, scale } from 'svelte/transition';
  import ChannelEmojiPicker from './ChannelEmojiPicker.svelte';

  export let isSubmitting = false;

  const dispatch = createEventDispatcher<{
    close: undefined;
    submit: {
      name: string;
      channelEmoji: string;
      channelType: 'TEXT' | 'VOICE';
      topic: string;
      isPublic: boolean;
    };
  }>();

  let name = '';
  let channelEmoji = '';
  let channelType: 'TEXT' | 'VOICE' = 'TEXT';
  let topic = '';
  let isPublic = true;

  function requestClose(): void {
    if (isSubmitting) {
      return;
    }
    dispatch('close');
  }

  function handleOverlayPointerDown(event: PointerEvent): void {
    if (event.target !== event.currentTarget) {
      return;
    }
    requestClose();
  }

  function handleWindowKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      requestClose();
    }
  }

  function submit(): void {
    if (isSubmitting || !name.trim()) {
      return;
    }

    dispatch('submit', {
      name: name.trim(),
      channelEmoji: channelEmoji.trim(),
      channelType,
      topic: topic.trim(),
      isPublic,
    });
  }

</script>

<svelte:window on:keydown={handleWindowKeydown} />

<div
  class="create-channel-modal-overlay"
  role="presentation"
  on:pointerdown={handleOverlayPointerDown}
  in:fade={{ duration: 150 }}
  out:fade={{ duration: 130 }}
>
  <div
    class="glass-panel-strong create-channel-modal"
    role="dialog"
    aria-modal="true"
    in:scale={{ duration: 180, start: 0.96 }}
    out:scale={{ duration: 140, start: 1 }}
  >
    <form on:submit|preventDefault={submit}>
      <div class="create-channel-modal-header">
        <h2 class="create-channel-modal-title">Create channel</h2>
        <button
          type="button"
          class="create-channel-modal-close-button"
          on:click={requestClose}
          disabled={isSubmitting}
        >
          Close
        </button>
      </div>

      <div class="create-channel-modal-fields">
        <label class="create-channel-modal-label">
          Name
          <input
            bind:value={name}
            type="text"
            class="create-channel-modal-input"
            placeholder="general"
            required
          />
        </label>

        <label class="create-channel-modal-label">
          Channel emoji (optional)
          <ChannelEmojiPicker bind:value={channelEmoji} disabled={isSubmitting} />
        </label>

        <label class="create-channel-modal-label">
          Channel type
          <select
            bind:value={channelType}
            class="create-channel-modal-select"
          >
            <option value="TEXT">TEXT</option>
            <option value="VOICE">VOICE</option>
          </select>
        </label>

        <label class="create-channel-modal-label">
          Topic (optional)
          <input
            bind:value={topic}
            type="text"
            class="create-channel-modal-input"
            placeholder="Channel description"
          />
        </label>

        <label class="create-channel-modal-label">
          Visibility
          <select
            bind:value={isPublic}
            class="create-channel-modal-select"
          >
            <option value={true}>Public</option>
            <option value={false}>Private</option>
          </select>
        </label>
      </div>

      <div class="create-channel-modal-actions">
        <button
          type="submit"
          class="create-channel-modal-button create-channel-modal-button-primary"
          disabled={isSubmitting || !name.trim()}
        >
          {isSubmitting ? 'Creating...' : 'Create'}
        </button>
        <button
          type="button"
          class="create-channel-modal-button create-channel-modal-button-secondary"
          on:click={requestClose}
          disabled={isSubmitting}
        >
          Cancel
        </button>
      </div>
    </form>
  </div>
</div>

<style>
  .create-channel-modal-overlay {
    @apply fixed inset-0 z-[80] flex items-center justify-center bg-surface-950/80 px-4 backdrop-blur-sm;
  }

  .create-channel-modal {
    @apply w-full max-w-md rounded-[1.1rem] p-5;
  }

  .create-channel-modal-header {
    @apply mb-4 flex items-center justify-between;
  }

  .create-channel-modal-title {
    @apply text-lg font-semibold text-slate-100;
  }

  .create-channel-modal-close-button {
    @apply rounded-lg border border-white/15 px-2 py-1 text-xs text-muted-200 transition hover:border-glass-highlight hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-60;
  }

  .create-channel-modal-fields {
    @apply space-y-3;
  }

  .create-channel-modal-label {
    @apply block text-sm text-muted-100;
  }

  .create-channel-modal-input {
    @apply mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400;
  }

  .create-channel-modal-select {
    @apply mt-1 w-full rounded-xl border border-white/15 bg-surface-900 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-accent-400;
  }

  .create-channel-modal-actions {
    @apply mt-5 flex gap-2;
  }

  .create-channel-modal-button {
    @apply rounded-xl px-4 py-2 text-sm transition disabled:cursor-not-allowed disabled:opacity-60;
  }

  .create-channel-modal-button-primary {
    @apply flex-1 bg-accent-500 font-medium text-white hover:bg-accent-400 disabled:bg-surface-800;
  }

  .create-channel-modal-button-secondary {
    @apply border border-white/15 text-muted-200 hover:border-glass-highlight hover:text-slate-100;
  }
</style>
