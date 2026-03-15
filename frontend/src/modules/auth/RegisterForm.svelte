<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { ArrowRight, UserPlus } from 'lucide-svelte';
  import { loginWithPassword } from '../../lib/auth';
  import { registerWithPassword } from './api';

  const dispatch = createEventDispatcher<{ authenticated: undefined; switchToLogin: undefined }>();

  let email = '';
  let password = '';
  let confirmPassword = '';
  let displayName = '';
  let isSubmitting = false;
  let error = '';
  $: hasMinLength = password.length >= 10;
  $: hasLower = /[a-z]/.test(password);
  $: hasUpper = /[A-Z]/.test(password);
  $: hasDigit = /[0-9]/.test(password);
  $: hasSpecial = /[^A-Za-z0-9]/.test(password);

  function requirementClass(isMet: boolean): string {
    return isMet ? 'text-emerald-300' : 'text-muted-400';
  }

  async function submit(): Promise<void> {
    const trimmedEmail = email.trim();
    const trimmedDisplayName = displayName.trim();

    if (!trimmedEmail || !password || !confirmPassword || isSubmitting) {
      return;
    }

    if (password !== confirmPassword) {
      error = 'Passwords do not match.';
      return;
    }

    isSubmitting = true;
    error = '';

    const registrationResult = await registerWithPassword({
      email: trimmedEmail,
      password,
      confirmPassword,
      displayName: trimmedDisplayName,
    });
    if (!registrationResult.ok) {
      error = registrationResult.error;
      isSubmitting = false;
      return;
    }

    const loginResult = await loginWithPassword(trimmedEmail, password);
    isSubmitting = false;

    if (!loginResult.ok) {
      error = loginResult.error ?? 'Account created, but sign-in failed.';
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
        <UserPlus class="h-4 w-4" />
      </div>
      <h1 class="auth-title">Sign up</h1>
    </div>
    <p class="auth-copy">Create an account to start using NestChat.</p>

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

    <label class="auth-field">
      Display name (optional)
      <input
        type="text"
        autocomplete="nickname"
        bind:value={displayName}
        class="auth-input"
        placeholder="Twoja nazwa"
      />
    </label>

    <label class="auth-field">
      Password
      <input
        type="password"
        autocomplete="new-password"
        bind:value={password}
        class="auth-input"
        placeholder="••••••••"
        required
      />
    </label>

    <label class="auth-field auth-field-spaced">
      Confirm password
      <input
        type="password"
        autocomplete="new-password"
        bind:value={confirmPassword}
        class="auth-input"
        placeholder="••••••••"
        required
      />
    </label>

    <ul class="auth-requirements">
      <li class={requirementClass(hasMinLength)}>• Minimum 10 characters</li>
      <li class={requirementClass(hasLower)}>• At least one lowercase letter (a-z)</li>
      <li class={requirementClass(hasUpper)}>• At least one uppercase letter (A-Z)</li>
      <li class={requirementClass(hasDigit)}>• At least one digit (0-9)</li>
      <li class={requirementClass(hasSpecial)}>• At least one special character (e.g. !@#$%)</li>
    </ul>

    <button
      type="submit"
      disabled={isSubmitting || !email.trim() || !password || !confirmPassword}
      class="auth-button auth-button-primary"
    >
      {#if isSubmitting}
        Creating account...
      {:else}
        Sign up
        <ArrowRight class="h-4 w-4" />
      {/if}
    </button>

    <button
      type="button"
      class="auth-button auth-button-secondary"
      on:click={() => dispatch('switchToLogin')}
    >
      Already have an account?
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

  .auth-requirements {
    @apply mb-5 space-y-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs;
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
