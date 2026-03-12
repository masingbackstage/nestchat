<script lang="ts">
  import { activeServer } from '../../../lib/stores/ui';
  import { ensureServerMembers, membersByServer, membersQueryStateByServer } from './store';
  import { getInitials } from './utils';

  $: currentServerUuid = $activeServer?.uuid ?? null;
  $: currentGroups = currentServerUuid ? ($membersByServer[currentServerUuid] ?? []) : [];
  $: currentQuery = currentServerUuid ? $membersQueryStateByServer[currentServerUuid] : null;
  $: totalMembers = currentGroups.reduce((total, group) => total + group.members.length, 0);

  function retryLoadMembers(): void {
    if (!currentServerUuid) {
      return;
    }
    void ensureServerMembers(currentServerUuid, true);
  }
</script>

<aside class="members-sidebar glass-panel" aria-label="Members">
  <header class="members-header">
    <h3 class="members-title">Members</h3>
    <span class="members-count">
      {totalMembers}
    </span>
  </header>

  <div class="members-body app-scrollbar">
    {#if !currentServerUuid}
      <p class="members-empty-state">No server selected.</p>
    {:else if currentQuery?.isLoading && currentGroups.length === 0}
      <div class="members-loading">
        <div class="members-loading-line"></div>
        <div class="members-loading-card"></div>
        <div class="members-loading-card"></div>
      </div>
    {:else if currentQuery?.error && currentGroups.length === 0}
      <div class="members-error-state">
        <p class="members-error-text">Failed to load members.</p>
        <button type="button" class="members-retry-button" on:click={retryLoadMembers}>
          Retry
        </button>
      </div>
    {:else if currentGroups.length === 0}
      <p class="members-empty-state">No members to display.</p>
    {:else}
      <div class="members-groups">
        {#each currentGroups as group (group.key)}
          <section class="members-group">
            <p class="members-group-label">
              {group.label} — {group.members.length}
            </p>
            <div class="members-list">
              {#each group.members as member (member.uuid)}
                <div class="member-row">
                  {#if member.avatarUrl}
                    <img src={member.avatarUrl} alt={member.displayName} class="member-avatar" />
                  {:else}
                    <div class="member-avatar member-avatar-fallback">
                      {getInitials(member.displayName)}
                    </div>
                  {/if}
                  <div class="member-content">
                    <p class="member-name">{member.displayName}</p>
                    {#if member.customStatus}
                      <p class="member-status-text">{member.customStatus}</p>
                    {/if}
                  </div>
                  <span
                    class:member-presence-online={member.isOnline}
                    class:member-presence-offline={!member.isOnline}
                    class="member-presence"
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

<style>
  .members-sidebar {
    @apply hidden w-[250px] shrink-0 rounded-panel xl:flex xl:flex-col;
  }

  .members-header {
    @apply flex items-center justify-between border-b border-white/10 px-5 py-4;
  }

  .members-title {
    @apply text-xs font-semibold uppercase tracking-[0.18em] text-muted-300;
  }

  .members-count {
    @apply rounded-pill bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-slate-100;
  }

  .members-body {
    @apply flex-1 overflow-auto px-4 py-4;
  }

  .members-empty-state {
    @apply rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-muted-200;
  }

  .members-loading {
    @apply space-y-3;
  }

  .members-loading-line {
    @apply h-3 w-28 animate-pulse rounded bg-white/10;
  }

  .members-loading-card {
    @apply h-10 animate-pulse rounded-xl bg-white/5;
  }

  .members-error-state {
    @apply rounded-xl border border-red-500/30 bg-red-500/10 p-3;
  }

  .members-error-text {
    @apply text-sm text-red-200;
  }

  .members-retry-button {
    @apply mt-2 rounded-lg border border-white/15 px-2.5 py-1 text-xs text-muted-100 transition hover:border-glass-highlight;
  }

  .members-groups {
    @apply space-y-6;
  }

  .members-group-label {
    @apply mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-500;
  }

  .members-list {
    @apply space-y-1.5;
  }

  .member-row {
    @apply flex items-center gap-2 rounded-xl px-2 py-1.5 transition hover:bg-white/5;
  }

  .member-avatar {
    @apply h-8 w-8 rounded-lg object-cover;
  }

  .member-avatar-fallback {
    @apply flex items-center justify-center bg-surface-800 text-[11px] font-semibold text-muted-200;
  }

  .member-content {
    @apply min-w-0 flex-1;
  }

  .member-name {
    @apply truncate text-sm font-semibold text-slate-100;
  }

  .member-status-text {
    @apply truncate text-[10px] text-muted-400;
  }

  .member-presence {
    @apply h-2.5 w-2.5 rounded-full border border-surface-950;
  }

  .member-presence-online {
    @apply bg-emerald-400;
  }

  .member-presence-offline {
    @apply bg-slate-500;
  }
</style>
