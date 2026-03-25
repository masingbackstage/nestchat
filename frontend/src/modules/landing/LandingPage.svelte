<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { ArrowRight, LogIn } from 'lucide-svelte';

  const dispatch = createEventDispatcher<{
    startLogin: undefined;
    startRegister: undefined;
  }>();
</script>

<div class="landing-shell app-shell">
  <div class="landing-blob landing-blob-left ambient-blob"></div>
  <div class="landing-blob landing-blob-right ambient-blob"></div>
  <div class="landing-blob landing-blob-bottom ambient-blob"></div>

  <main class="landing-main">
    <section class="landing-panel glass-panel">
      <h1 class="landing-title text-gradient">NESTCHAT</h1>

      <p class="landing-copy">EAGLE</p>

      <div class="landing-actions">
        <button
          type="button"
          class="landing-button landing-button-primary"
          on:click={() => dispatch('startRegister')}
        >
          Sign up
          <ArrowRight class="landing-icon" />
        </button>
        <button
          type="button"
          class="landing-button landing-button-secondary"
          on:click={() => dispatch('startLogin')}
        >
          <LogIn class="landing-icon" />
          Sign in
        </button>
      </div>
    </section>
  </main>
</div>

<style>
  .landing-main {
    @apply relative mx-auto flex min-h-[calc(100vh-1rem)] w-full max-w-6xl items-center justify-center;
  }

  .landing-panel {
    @apply w-full rounded-[2rem] px-8 py-12 md:px-14 md:py-16;
  }

  .landing-title {
    @apply max-w-3xl text-4xl font-semibold leading-tight md:text-6xl;
  }

  .landing-copy {
    @apply mt-6 max-w-2xl text-base leading-relaxed text-muted-200 md:text-lg;
  }

  .landing-actions {
    @apply mt-10 flex flex-col gap-3 sm:flex-row;
  }

  .landing-button {
    @apply inline-flex items-center justify-center gap-2 rounded-xl px-6 py-3 text-sm font-medium transition;
  }

  .landing-button-primary {
    @apply bg-accent-500 text-white hover:bg-accent-400;
  }

  .landing-button-secondary {
    @apply border border-white/15 bg-white/5 text-muted-100 hover:border-glass-highlight hover:bg-white/10 hover:text-white;
  }

  .landing-blob-left {
    @apply left-[-14%] top-[-10%] h-[520px] w-[520px] bg-accent-500/20;
  }

  .landing-blob-right {
    @apply right-[-8%] top-[6%] h-[500px] w-[500px] bg-indigo-500/25;
  }

  .landing-blob-bottom {
    @apply bottom-[-18%] left-[25%] h-[450px] w-[450px] bg-cyan-500/15;
  }
</style>
