<script lang="ts">
  import { createEventDispatcher } from 'svelte';
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
    return isMet ? 'text-emerald-300' : 'text-slate-400';
  }

  async function submit(): Promise<void> {
    const trimmedEmail = email.trim();
    const trimmedDisplayName = displayName.trim();

    if (!trimmedEmail || !password || !confirmPassword || isSubmitting) {
      return;
    }

    if (password !== confirmPassword) {
      error = 'Hasła nie są takie same.';
      return;
    }

    isSubmitting = true;
    error = '';

    const baseUrl = import.meta.env.VITE_API_URL;
    if (!baseUrl) {
      error = 'Brak VITE_API_URL.';
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
          error = firstEntry[0] ?? 'Nie udało się zarejestrować.';
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
      error = loginResult.error ?? 'Konto utworzone, ale logowanie nie powiodło się.';
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
    <h1 class="mb-1 text-xl font-semibold text-slate-100">Załóż konto</h1>
    <p class="mb-5 text-sm text-slate-400">Utwórz konto, aby zacząć korzystać z NestChat.</p>

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

    <label class="mb-3 block text-sm text-slate-300">
      Display name (opcjonalnie)
      <input
        type="text"
        autocomplete="nickname"
        bind:value={displayName}
        class="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
        placeholder="Twoja nazwa"
      />
    </label>

    <label class="mb-3 block text-sm text-slate-300">
      Hasło
      <input
        type="password"
        autocomplete="new-password"
        bind:value={password}
        class="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
        placeholder="••••••••"
        required
      />
    </label>

    <label class="mb-5 block text-sm text-slate-300">
      Powtórz hasło
      <input
        type="password"
        autocomplete="new-password"
        bind:value={confirmPassword}
        class="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
        placeholder="••••••••"
        required
      />
    </label>

    <ul class="mb-5 space-y-1 rounded border border-slate-800 bg-slate-900/40 px-3 py-2 text-xs">
      <li class={requirementClass(hasMinLength)}>• Minimum 10 znaków</li>
      <li class={requirementClass(hasLower)}>• Co najmniej jedna mała litera (a-z)</li>
      <li class={requirementClass(hasUpper)}>• Co najmniej jedna duża litera (A-Z)</li>
      <li class={requirementClass(hasDigit)}>• Co najmniej jedna cyfra (0-9)</li>
      <li class={requirementClass(hasSpecial)}>
        • Co najmniej jeden znak specjalny (np. !@#$%)
      </li>
    </ul>

    <button
      type="submit"
      disabled={isSubmitting || !email.trim() || !password || !confirmPassword}
      class="w-full rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-700"
    >
      {#if isSubmitting}
        Tworzenie konta...
      {:else}
        Zarejestruj
      {/if}
    </button>

    <button
      type="button"
      class="mt-3 w-full rounded border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
      on:click={() => dispatch('switchToLogin')}
    >
      Mam już konto
    </button>
  </form>
</div>
