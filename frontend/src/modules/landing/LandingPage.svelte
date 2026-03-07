<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { ArrowRight, LogIn } from 'lucide-svelte';

  const dispatch = createEventDispatcher<{
    startLogin: undefined;
    startRegister: undefined;
  }>();
</script>

<div class="app-shell">
  <div class="ambient-blob left-[-14%] top-[-10%] h-[520px] w-[520px] bg-accent-500/20"></div>
  <div class="ambient-blob right-[-8%] top-[6%] h-[500px] w-[500px] bg-indigo-500/25"></div>
  <div class="ambient-blob bottom-[-18%] left-[25%] h-[450px] w-[450px] bg-cyan-500/15"></div>

  <main class="relative mx-auto flex min-h-[calc(100vh-1rem)] w-full max-w-6xl items-center justify-center">
    <section class="glass-panel w-full rounded-[2rem] px-8 py-12 md:px-14 md:py-16">
      <p class="mb-5 inline-flex w-fit rounded-pill border border-white/15 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.18em] text-muted-200">
        NestChat
      </p>

      <h1 class="text-gradient max-w-3xl text-4xl font-semibold leading-tight md:text-6xl">
        Team chat that never loses context.
      </h1>

      <p class="mt-6 max-w-2xl text-base leading-relaxed text-muted-200 md:text-lg">
        Channels, roles, realtime updates, pagination, and message moderation in one interface.
      </p>

      <div class="mt-10 flex flex-col gap-3 sm:flex-row">
      <button
        type="button"
        class="inline-flex items-center justify-center gap-2 rounded-xl bg-accent-500 px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-400"
        on:click={() => dispatch('startRegister')}
      >
        Sign up
        <ArrowRight class="h-4 w-4" />
      </button>
      <button
        type="button"
        class="inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/5 px-6 py-3 text-sm font-medium text-muted-100 transition hover:border-glass-highlight hover:bg-white/10 hover:text-white"
        on:click={() => dispatch('startLogin')}
      >
        <LogIn class="h-4 w-4" />
        Sign in
      </button>
    </div>
  </section>
  </main>
</div>
