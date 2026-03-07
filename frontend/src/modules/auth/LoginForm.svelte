<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { ArrowRight, UserRound } from 'lucide-svelte';
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
      error = result.error ?? 'Login failed.';
      return;
    }

    dispatch('authenticated');
  }

</script>

<div class="app-shell flex items-center justify-center px-4">
  <div class="ambient-blob left-[-14%] top-[-10%] h-[460px] w-[460px] bg-accent-500/20"></div>
  <div class="ambient-blob right-[-10%] top-[10%] h-[420px] w-[420px] bg-indigo-500/20"></div>
  <form
    class="glass-panel w-full max-w-sm rounded-[1.1rem] p-6"
    on:submit|preventDefault={submit}
  >
    <div class="mb-4 flex items-center gap-2">
      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-500/20 text-accent-300">
        <UserRound class="h-4 w-4" />
      </div>
      <h1 class="text-xl font-semibold text-slate-100">Sign in</h1>
    </div>
    <p class="mb-5 text-sm text-muted-200">Sign in to continue to NestChat.</p>

    {#if error}
      <p class="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
        {error}
      </p>
    {/if}

    <label class="mb-3 block text-sm text-muted-100">
      Email
      <input
        type="email"
        autocomplete="email"
        bind:value={email}
        class="mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400"
        placeholder="you@example.com"
        required
      />
    </label>

    <label class="mb-5 block text-sm text-muted-100">
      Password
      <input
        type="password"
        autocomplete="current-password"
        bind:value={password}
        class="mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400"
        placeholder="••••••••"
        required
      />
    </label>

    <button
      type="submit"
      disabled={isSubmitting || !email.trim() || !password}
      class="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-surface-800"
    >
      {#if isSubmitting}
        Logowanie...
      {:else}
        Sign in
        <ArrowRight class="h-4 w-4" />
      {/if}
    </button>

    <button
      type="button"
      class="mt-3 w-full rounded-xl border border-white/15 px-4 py-2 text-sm font-medium text-muted-200 transition hover:border-glass-highlight hover:text-slate-100"
      on:click={() => dispatch('switchToRegister')}
    >
      Don't have an account?
    </button>
  </form>
</div>
