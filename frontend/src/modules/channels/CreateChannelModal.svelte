<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { fade, scale } from 'svelte/transition';

  export let isSubmitting = false;

  const dispatch = createEventDispatcher<{
    close: undefined;
    submit: {
      name: string;
      channelType: 'TEXT' | 'VOICE';
      topic: string;
      isPublic: boolean;
    };
  }>();

  let name = '';
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
      channelType,
      topic: topic.trim(),
      isPublic,
    });
  }
</script>

<svelte:window on:keydown={handleWindowKeydown} />

<div
  class="fixed inset-0 z-[80] flex items-center justify-center bg-surface-950/80 px-4 backdrop-blur-sm"
  role="presentation"
  on:pointerdown={handleOverlayPointerDown}
  in:fade={{ duration: 150 }}
  out:fade={{ duration: 130 }}
>
  <div
    class="glass-panel-strong w-full max-w-md rounded-[1.1rem] p-5"
    role="dialog"
    aria-modal="true"
    in:scale={{ duration: 180, start: 0.96 }}
    out:scale={{ duration: 140, start: 1 }}
  >
    <form on:submit|preventDefault={submit}>
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-slate-100">Create channel</h2>
        <button
          type="button"
          class="rounded-lg border border-white/15 px-2 py-1 text-xs text-muted-200 transition hover:border-glass-highlight hover:text-slate-100"
          on:click={requestClose}
          disabled={isSubmitting}
        >
          Close
        </button>
      </div>

      <div class="space-y-3">
        <label class="block text-sm text-muted-100">
          Name
          <input
            bind:value={name}
            type="text"
            class="mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400"
            placeholder="general"
            required
          />
        </label>

        <label class="block text-sm text-muted-100">
          Channel type
          <select
            bind:value={channelType}
            class="mt-1 w-full rounded-xl border border-white/15 bg-surface-900 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-accent-400"
          >
            <option value="TEXT">TEXT</option>
            <option value="VOICE">VOICE</option>
          </select>
        </label>

        <label class="block text-sm text-muted-100">
          Topic (optional)
          <input
            bind:value={topic}
            type="text"
            class="mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400"
            placeholder="Channel description"
          />
        </label>

        <label class="block text-sm text-muted-100">
          Visibility
          <select
            bind:value={isPublic}
            class="mt-1 w-full rounded-xl border border-white/15 bg-surface-900 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-accent-400"
          >
            <option value={true}>Public</option>
            <option value={false}>Private</option>
          </select>
        </label>
      </div>

      <div class="mt-5 flex gap-2">
        <button
          type="submit"
          class="flex-1 rounded-xl bg-accent-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-surface-800"
          disabled={isSubmitting || !name.trim()}
        >
          {isSubmitting ? 'Creating...' : 'Create'}
        </button>
        <button
          type="button"
          class="rounded-xl border border-white/15 px-4 py-2 text-sm text-muted-200 transition hover:border-glass-highlight hover:text-slate-100"
          on:click={requestClose}
          disabled={isSubmitting}
        >
          Cancel
        </button>
      </div>
    </form>
  </div>
</div>
