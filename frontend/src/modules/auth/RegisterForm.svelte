<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { ArrowRight, UserPlus } from 'lucide-svelte';
  import { loginWithPassword } from '../../lib/auth';

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

    const baseUrl = import.meta.env.VITE_API_URL;
    if (!baseUrl) {
      error = 'Missing VITE_API_URL.';
      isSubmitting = false;
      return;
    }

    const response = await fetch(`${baseUrl}/auth/registration/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: trimmedEmail,
        password1: password,
        password2: confirmPassword,
        displayName: trimmedDisplayName,
      }),
    });

    if (!response.ok) {
      try {
        const payload = (await response.json()) as Record<string, string[] | string>;
        const preferredKeys = [
          'password1',
          'password2',
          'email',
          'displayName',
          'display_name',
          'nonFieldErrors',
          'non_field_errors',
          'detail',
        ];
        const firstEntry =
          preferredKeys.map((key) => payload[key]).find((value) => value !== undefined) ??
          Object.values(payload)[0];
        if (Array.isArray(firstEntry) && firstEntry.length > 0) {
          error = firstEntry[0] ?? 'Registration failed.';
        } else if (typeof firstEntry === 'string') {
          error = firstEntry;
        } else {
          error = `HTTP ${response.status}`;
        }
      } catch {
        error = `HTTP ${response.status}`;
      }
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

<div class="app-shell flex items-center justify-center px-4">
  <div class="ambient-blob left-[-14%] top-[-10%] h-[460px] w-[460px] bg-accent-500/20"></div>
  <div class="ambient-blob right-[-10%] top-[10%] h-[420px] w-[420px] bg-indigo-500/20"></div>
  <form class="glass-panel w-full max-w-sm rounded-[1.1rem] p-6" on:submit|preventDefault={submit}>
    <div class="mb-4 flex items-center gap-2">
      <div
        class="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-500/20 text-accent-300"
      >
        <UserPlus class="h-4 w-4" />
      </div>
      <h1 class="text-xl font-semibold text-slate-100">Sign up</h1>
    </div>
    <p class="mb-5 text-sm text-muted-200">Create an account to start using NestChat.</p>

    {#if error}
      <p
        class="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300"
      >
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

    <label class="mb-3 block text-sm text-muted-100">
      Display name (optional)
      <input
        type="text"
        autocomplete="nickname"
        bind:value={displayName}
        class="mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400"
        placeholder="Twoja nazwa"
      />
    </label>

    <label class="mb-3 block text-sm text-muted-100">
      Password
      <input
        type="password"
        autocomplete="new-password"
        bind:value={password}
        class="mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400"
        placeholder="••••••••"
        required
      />
    </label>

    <label class="mb-5 block text-sm text-muted-100">
      Confirm password
      <input
        type="password"
        autocomplete="new-password"
        bind:value={confirmPassword}
        class="mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400"
        placeholder="••••••••"
        required
      />
    </label>

    <ul class="mb-5 space-y-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs">
      <li class={requirementClass(hasMinLength)}>• Minimum 10 characters</li>
      <li class={requirementClass(hasLower)}>• At least one lowercase letter (a-z)</li>
      <li class={requirementClass(hasUpper)}>• At least one uppercase letter (A-Z)</li>
      <li class={requirementClass(hasDigit)}>• At least one digit (0-9)</li>
      <li class={requirementClass(hasSpecial)}>• At least one special character (e.g. !@#$%)</li>
    </ul>

    <button
      type="submit"
      disabled={isSubmitting || !email.trim() || !password || !confirmPassword}
      class="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-surface-800"
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
      class="mt-3 w-full rounded-xl border border-white/15 px-4 py-2 text-sm font-medium text-muted-200 transition hover:border-glass-highlight hover:text-slate-100"
      on:click={() => dispatch('switchToLogin')}
    >
      Already have an account?
    </button>
  </form>
</div>
