<script lang="ts">
  import { activeServer } from '../../lib/stores/ui';
  import { ensureServerMembers, membersByServer, membersQueryStateByServer } from './members.store';

  $: currentServerUuid = $activeServer?.uuid ?? null;
  $: currentGroups = currentServerUuid ? ($membersByServer[currentServerUuid] ?? []) : [];
  $: currentQuery = currentServerUuid ? $membersQueryStateByServer[currentServerUuid] : null;
  $: totalMembers = currentGroups.reduce((total, group) => total + group.members.length, 0);

  function getInitials(displayName: string): string {
    const parts = displayName.trim().split(/\s+/).filter(Boolean).slice(0, 2);
    if (parts.length === 0) {
      return '?';
    }
    return parts.map((part) => part[0]?.toUpperCase() ?? '').join('');
  }

  function retryLoadMembers(): void {
    if (!currentServerUuid) {
      return;
    }
    void ensureServerMembers(currentServerUuid, true);
  }
</script>

<aside
  class="glass-panel hidden w-[250px] shrink-0 rounded-panel xl:flex xl:flex-col"
  aria-label="Members"
>
  <header class="flex items-center justify-between border-b border-white/10 px-5 py-4">
    <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-muted-300">Members</h3>
    <span class="rounded-pill bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-slate-100">
      {totalMembers}
    </span>
  </header>

  <div class="app-scrollbar flex-1 overflow-auto px-4 py-4">
    {#if !currentServerUuid}
      <p class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-muted-200">
        No server selected.
      </p>
    {:else if currentQuery?.isLoading && currentGroups.length === 0}
      <div class="space-y-3">
        <div class="h-3 w-28 animate-pulse rounded bg-white/10"></div>
        <div class="h-10 animate-pulse rounded-xl bg-white/5"></div>
        <div class="h-10 animate-pulse rounded-xl bg-white/5"></div>
      </div>
    {:else if currentQuery?.error && currentGroups.length === 0}
      <div class="rounded-xl border border-red-500/30 bg-red-500/10 p-3">
        <p class="text-sm text-red-200">Failed to load members.</p>
        <button
          type="button"
          class="mt-2 rounded-lg border border-white/15 px-2.5 py-1 text-xs text-muted-100 transition hover:border-glass-highlight"
          on:click={retryLoadMembers}
        >
          Retry
        </button>
      </div>
    {:else if currentGroups.length === 0}
      <p class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-muted-200">
        No members to display.
      </p>
    {:else}
      <div class="space-y-6">
        {#each currentGroups as group (group.key)}
          <section>
            <p class="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-500">
              {group.label} — {group.members.length}
            </p>
            <div class="space-y-1.5">
              {#each group.members as member (member.uuid)}
                <div
                  class="flex items-center gap-2 rounded-xl px-2 py-1.5 transition hover:bg-white/5"
                >
                  {#if member.avatar}
                    <img
                      src={member.avatar}
                      alt={member.displayName}
                      class="h-8 w-8 rounded-lg object-cover"
                    />
                  {:else}
                    <div
                      class="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-800 text-[11px] font-semibold text-muted-200"
                    >
                      {getInitials(member.displayName)}
                    </div>
                  {/if}
                  <div class="min-w-0 flex-1">
                    <p class="truncate text-sm font-semibold text-slate-100">
                      {member.displayName}
                    </p>
                    {#if member.customStatus}
                      <p class="truncate text-[10px] text-muted-400">{member.customStatus}</p>
                    {/if}
                  </div>
                  <span
                    class={`h-2.5 w-2.5 rounded-full border border-surface-950 ${
                      member.isOnline ? 'bg-emerald-400' : 'bg-slate-500'
                    }`}
                  ></span>
                </div>
              {/each}
            </div>
          </section>
        {/each}
      </div>
    {/if}
  </div>
</aside>
