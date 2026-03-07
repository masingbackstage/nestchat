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
  class="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/70 px-4"
  role="presentation"
  on:pointerdown={handleOverlayPointerDown}
  in:fade={{ duration: 150 }}
  out:fade={{ duration: 130 }}
>
  <div
    class="w-full max-w-md rounded-lg border border-slate-700 bg-app-900 p-5 shadow-2xl"
    role="dialog"
    aria-modal="true"
    in:scale={{ duration: 180, start: 0.96 }}
    out:scale={{ duration: 140, start: 1 }}
  >
    <form on:submit|preventDefault={submit}>
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-slate-100">Utwórz kanał</h2>
        <button
          type="button"
          class="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
          on:click={requestClose}
          disabled={isSubmitting}
        >
          Zamknij
        </button>
      </div>

      <div class="space-y-3">
        <label class="block text-sm text-slate-300">
          Nazwa
          <input
            bind:value={name}
            type="text"
            class="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
            placeholder="general"
            required
          />
        </label>

        <label class="block text-sm text-slate-300">
          Typ kanału
          <select
            bind:value={channelType}
            class="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
          >
            <option value="TEXT">TEXT</option>
            <option value="VOICE">VOICE</option>
          </select>
        </label>

        <label class="block text-sm text-slate-300">
          Topic (opcjonalnie)
          <input
            bind:value={topic}
            type="text"
            class="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
            placeholder="Opis kanału"
          />
        </label>

        <label class="block text-sm text-slate-300">
          Widoczność
          <select
            bind:value={isPublic}
            class="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
          >
            <option value={true}>Publiczny</option>
            <option value={false}>Prywatny</option>
          </select>
        </label>
      </div>

      <div class="mt-5 flex gap-2">
        <button
          type="submit"
          class="flex-1 rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-700"
          disabled={isSubmitting || !name.trim()}
        >
          {isSubmitting ? 'Tworzenie...' : 'Utwórz'}
        </button>
        <button
          type="button"
          class="rounded border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
          on:click={requestClose}
          disabled={isSubmitting}
        >
          Anuluj
        </button>
      </div>
    </form>
  </div>
</div>
