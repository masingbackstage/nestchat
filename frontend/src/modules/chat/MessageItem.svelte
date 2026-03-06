<script lang="ts">
  import type { Message } from '../../types/gateway';

  export let message: Message;

  $: formattedTime = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '--:--';
</script>

<article class="rounded-md px-3 py-2 hover:bg-slate-800/50">
  <header class="mb-1 flex items-center gap-2">
    <span class="text-sm font-semibold text-slate-100">{message.author}</span>
    <time class="text-xs text-slate-500">{formattedTime}</time>
  </header>
  <p class="whitespace-pre-wrap break-words text-sm text-slate-300">{message.content}</p>
</article>
