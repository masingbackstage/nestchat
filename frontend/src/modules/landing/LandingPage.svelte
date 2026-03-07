<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{
    startLogin: undefined;
    startRegister: undefined;
  }>();
</script>

<div class="relative min-h-screen overflow-hidden bg-app-950 text-slate-100">
  <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(99,102,241,0.25),transparent_45%),radial-gradient(circle_at_80%_25%,rgba(20,184,166,0.2),transparent_45%),radial-gradient(circle_at_50%_100%,rgba(30,41,59,0.8),transparent_55%)]"></div>

  <main class="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center px-6 py-16 md:px-10">
    <p class="mb-4 inline-flex w-fit rounded-full border border-slate-700/70 bg-slate-900/60 px-3 py-1 text-xs uppercase tracking-[0.18em] text-slate-300">
      NestChat
    </p>

    <h1 class="max-w-3xl text-4xl font-semibold leading-tight text-slate-100 md:text-6xl">
      Team chat, który nie gubi kontekstu.
    </h1>

    <p class="mt-6 max-w-2xl text-base leading-relaxed text-slate-300 md:text-lg">
      Kanały, role, realtime i wydajny scroll historii. Jeden interfejs dla całego zespołu.
    </p>

    <div class="mt-10 flex flex-col gap-3 sm:flex-row">
      <button
        type="button"
        class="rounded-lg bg-indigo-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-indigo-500"
        on:click={() => dispatch('startRegister')}
      >
        Załóż konto
      </button>
      <button
        type="button"
        class="rounded-lg border border-slate-700 bg-slate-900/70 px-6 py-3 text-sm font-medium text-slate-200 transition hover:border-slate-500 hover:text-white"
        on:click={() => dispatch('startLogin')}
      >
        Zaloguj
      </button>
    </div>
  </main>
</div>
