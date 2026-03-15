<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { ArrowRight, UserRound } from 'lucide-svelte';
  import { loginWithPassword } from '../../lib/auth';

  const dispatch = createEventDispatcher<{
    authenticated: undefined;
    switchToRegister: undefined;
  }>();

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

<div class="app-shell auth-shell">
  <div class="ambient-blob auth-blob-left"></div>
  <div class="ambient-blob auth-blob-right"></div>
  <form class="glass-panel auth-card" on:submit|preventDefault={submit}>
    <div class="auth-header">
      <div class="auth-icon-badge">
        <UserRound class="h-4 w-4" />
      </div>
      <h1 class="auth-title">Sign in</h1>
    </div>
    <p class="auth-copy">Sign in to continue to NestChat.</p>

    {#if error}
      <p class="auth-error">{error}</p>
    {/if}

    <label class="auth-field">
      Email
      <input
        type="email"
        autocomplete="email"
        bind:value={email}
        class="auth-input"
        placeholder="you@example.com"
        required
      />
    </label>

    <label class="auth-field auth-field-spaced">
      Password
      <input
        type="password"
        autocomplete="current-password"
        bind:value={password}
        class="auth-input"
        placeholder="••••••••"
        required
      />
    </label>

    <button
      type="submit"
      disabled={isSubmitting || !email.trim() || !password}
      class="auth-button auth-button-primary"
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
      class="auth-button auth-button-secondary"
      on:click={() => dispatch('switchToRegister')}
    >
      Don't have an account?
    </button>
  </form>
</div>

<style>
  .auth-shell {
    @apply flex items-center justify-center px-4;
  }

  .auth-blob-left {
    @apply left-[-14%] top-[-10%] h-[460px] w-[460px] bg-accent-500/20;
  }

  .auth-blob-right {
    @apply right-[-10%] top-[10%] h-[420px] w-[420px] bg-indigo-500/20;
  }

  .auth-card {
    @apply w-full max-w-sm rounded-[1.1rem] p-6;
  }

  .auth-header {
    @apply mb-4 flex items-center gap-2;
  }

  .auth-icon-badge {
    @apply flex h-8 w-8 items-center justify-center rounded-lg bg-accent-500/20 text-accent-300;
  }

  .auth-title {
    @apply text-xl font-semibold text-slate-100;
  }

  .auth-copy {
    @apply mb-5 text-sm text-muted-200;
  }

  .auth-error {
    @apply mb-4 rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300;
  }

  .auth-field {
    @apply mb-3 block text-sm text-muted-100;
  }

  .auth-field-spaced {
    @apply mb-5;
  }

  .auth-input {
    @apply mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400;
  }

  .auth-button {
    @apply w-full rounded-xl px-4 py-2 text-sm font-medium transition;
  }

  .auth-button-primary {
    @apply inline-flex items-center justify-center gap-2 bg-accent-500 text-white hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-surface-800;
  }

  .auth-button-secondary {
    @apply mt-3 border border-white/15 text-muted-200 hover:border-glass-highlight hover:text-slate-100;
  }
</style>
