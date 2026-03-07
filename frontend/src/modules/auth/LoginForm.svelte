<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { loginWithPassword } from '../../lib/auth';

  const dispatch = createEventDispatcher<{ authenticated: undefined; switchToRegister: undefined }>();

  let email = '';
  let password = '';
  let isSubmitting = false;
  let error = '';

  async function submit(): Promise<void> {
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password || isSubmitting) {
      return;
    }

    isSubmitting = true;
    error = '';

    const result = await loginWithPassword(trimmedEmail, password);

    isSubmitting = false;

    if (!result.ok) {
      error = result.error ?? 'Nie udało się zalogować.';
      return;
    }

    dispatch('authenticated');
  }

</script>

<div class="flex min-h-screen items-center justify-center bg-app-950 px-4">
  <form
    class="w-full max-w-sm rounded-lg border border-slate-800 bg-app-900 p-6 shadow-lg"
    on:submit|preventDefault={submit}
  >
    <h1 class="mb-1 text-xl font-semibold text-slate-100">Zaloguj się</h1>
    <p class="mb-5 text-sm text-slate-400">Aby wejść do NestChat.</p>

    {#if error}
      <p class="mb-4 rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
        {error}
      </p>
    {/if}

    <label class="mb-3 block text-sm text-slate-300">
      Email
      <input
        type="email"
        autocomplete="email"
        bind:value={email}
        class="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
        placeholder="you@example.com"
        required
      />
    </label>

    <label class="mb-5 block text-sm text-slate-300">
      Hasło
      <input
        type="password"
        autocomplete="current-password"
        bind:value={password}
        class="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
        placeholder="••••••••"
        required
      />
    </label>

    <button
      type="submit"
      disabled={isSubmitting || !email.trim() || !password}
      class="w-full rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-700"
    >
      {#if isSubmitting}
        Logowanie...
      {:else}
        Zaloguj
      {/if}
    </button>

    <button
      type="button"
      class="mt-3 w-full rounded border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
      on:click={() => dispatch('switchToRegister')}
    >
      Nie mam konta
    </button>
  </form>
</div>
