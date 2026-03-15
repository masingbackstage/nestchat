<script lang="ts">
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { Search, X } from 'lucide-svelte';
  import { searchUsers } from '../friends';
  import type { UserSearchResult } from '../../../types/gateway';

  type SubmitPayload = {
    participantUuids: string[];
    title?: string;
  };

  export let isSubmitting = false;

  const dispatch = createEventDispatcher<{
    close: undefined;
    submit: SubmitPayload;
  }>();

  let mode: 'direct' | 'group' = 'direct';
  let title = '';
  let query = '';
  let error = '';
  let searchResults: UserSearchResult[] = [];
  let selectedUsers: UserSearchResult[] = [];
  let isSearching = false;
  let searchDebounce: ReturnType<typeof setTimeout> | null = null;

  function closeModal(): void {
    if (isSubmitting) {
      return;
    }
    dispatch('close');
  }

  function validateAndSubmit(): void {
    if (mode === 'direct' && selectedUsers.length !== 1) {
      error = 'Direct message requires exactly 1 recipient.';
      return;
    }
    if (mode === 'group' && selectedUsers.length < 2) {
      error = 'Group conversation requires at least 2 recipients.';
      return;
    }

    error = '';
    dispatch('submit', {
      participantUuids: selectedUsers.map((user) => user.uuid),
      ...(mode === 'group' && title.trim() ? { title: title.trim() } : {}),
    });
  }

  function onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      closeModal();
    }
  }

  function removeUser(uuid: string): void {
    selectedUsers = selectedUsers.filter((user) => user.uuid !== uuid);
  }

  function selectUser(user: UserSearchResult): void {
    if (selectedUsers.some((item) => item.uuid === user.uuid)) {
      return;
    }

    if (mode === 'direct') {
      selectedUsers = [user];
    } else {
      selectedUsers = [...selectedUsers, user];
    }

    query = '';
    searchResults = [];
  }

  async function runSearch(value: string): Promise<void> {
    const normalized = value.trim();
    if (normalized.length < 2) {
      searchResults = [];
      return;
    }

    isSearching = true;
    try {
      const results = await searchUsers(normalized);
      const selected = new Set(selectedUsers.map((user) => user.uuid));
      searchResults = results.filter((user) => !selected.has(user.uuid));
    } catch {
      searchResults = [];
    } finally {
      isSearching = false;
    }
  }

  $: if (mode === 'direct' && selectedUsers.length > 1) {
    selectedUsers = selectedUsers.slice(0, 1);
  }

  $: scheduleSearch(query);

  function scheduleSearch(nextQuery: string): void {
    if (searchDebounce) {
      clearTimeout(searchDebounce);
    }

    searchDebounce = setTimeout(() => {
      void runSearch(nextQuery);
    }, 250);
  }

  onMount(() => {
    window.addEventListener('keydown', onKeydown);
  });

  onDestroy(() => {
    window.removeEventListener('keydown', onKeydown);
    if (searchDebounce) {
      clearTimeout(searchDebounce);
    }
  });
</script>

<div class="dm-create-modal-overlay">
  <button
    type="button"
    aria-label="Close create conversation modal"
    class="dm-create-modal-backdrop"
    on:click={closeModal}
    disabled={isSubmitting}
  ></button>
  <section class="glass-panel glass-panel-strong dm-create-modal">
    <h2 class="dm-create-modal-title">New conversation</h2>
    <p class="dm-create-modal-copy">Search users by email, tag or display name.</p>

    {#if error}
      <p class="dm-create-modal-error">{error}</p>
    {/if}

    <div class="dm-create-modal-fields">
      <label class="dm-create-modal-field">
        <span>Type</span>
        <select
          bind:value={mode}
          class="dm-create-modal-select"
          disabled={isSubmitting}
        >
          <option value="direct">Direct (1:1)</option>
          <option value="group">Group</option>
        </select>
      </label>

      {#if mode === 'group'}
        <label class="dm-create-modal-field">
          <span>Title (optional)</span>
          <input
            type="text"
            bind:value={title}
            maxlength="120"
            placeholder="Project squad"
            class="dm-create-modal-input"
            disabled={isSubmitting}
          />
        </label>
      {/if}

      <label class="dm-create-modal-field">
        <span>Recipients</span>
        <div class="dm-create-modal-recipient-box">
          <div class="dm-create-modal-chips">
            {#each selectedUsers as user (user.uuid)}
              <span class="dm-create-modal-chip">
                {user.displayName ?? user.display_name ?? user.email}
                <button
                  type="button"
                  class="dm-create-modal-chip-button"
                  on:click={() => removeUser(user.uuid)}
                  aria-label="Remove recipient"
                >
                  <X class="h-3.5 w-3.5" />
                </button>
              </span>
          {/each}
          </div>

          <div class="dm-create-modal-search">
            <Search class="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-500" />
            <input
              type="text"
              bind:value={query}
              placeholder="Type at least 2 characters..."
              class="dm-create-modal-search-input"
              disabled={isSubmitting}
            />
          </div>

          {#if query.trim().length >= 2}
            <div class="app-scrollbar dm-create-modal-results">
              {#if isSearching}
                <p class="dm-create-modal-results-copy">Searching...</p>
              {:else if searchResults.length === 0}
                <p class="dm-create-modal-results-copy">No users found.</p>
              {:else}
                {#each searchResults as user (user.uuid)}
                  <button
                    type="button"
                    class="dm-create-modal-result"
                    on:click={() => selectUser(user)}
                  >
                    <div class="dm-create-modal-result-avatar">
                      {#if user.avatarUrl ?? user.avatar_url}
                        <img
                          src={user.avatarUrl ?? user.avatar_url}
                          alt={user.displayName ?? user.display_name ?? user.email}
                          class="dm-create-modal-result-avatar-image"
                        />
                      {/if}
                    </div>
                    <div class="dm-create-modal-result-content">
                      <p class="dm-create-modal-result-name">
                        {user.displayName ?? user.display_name ?? user.email}
                      </p>
                      <p class="dm-create-modal-result-email">{user.email}</p>
                    </div>
                  </button>
                {/each}
              {/if}
            </div>
          {/if}
        </div>
      </label>
    </div>

    <div class="dm-create-modal-actions">
      <button
        type="button"
        class="dm-create-modal-button dm-create-modal-button-secondary"
        on:click={closeModal}
        disabled={isSubmitting}
      >
        Cancel
      </button>
      <button
        type="button"
        class="dm-create-modal-button dm-create-modal-button-primary"
        on:click={validateAndSubmit}
        disabled={isSubmitting}
      >
        {isSubmitting ? 'Creating...' : 'Create'}
      </button>
    </div>
  </section>
</div>

<style>
  .dm-create-modal-overlay {
    @apply fixed inset-0 z-[70] flex items-center justify-center bg-black/55 px-4 py-6;
  }

  .dm-create-modal-backdrop {
    @apply absolute inset-0 cursor-default bg-transparent;
  }

  .dm-create-modal {
    @apply relative z-10 w-full max-w-lg rounded-2xl p-5;
  }

  .dm-create-modal-title {
    @apply text-lg font-semibold text-slate-100;
  }

  .dm-create-modal-copy {
    @apply mt-1 text-sm text-muted-300;
  }

  .dm-create-modal-error {
    @apply mt-3 rounded-xl border border-red-400/50 bg-red-500/10 px-3 py-2 text-sm text-red-200;
  }

  .dm-create-modal-fields {
    @apply mt-4 space-y-3;
  }

  .dm-create-modal-field {
    @apply flex flex-col gap-1.5 text-sm text-slate-200;
  }

  .dm-create-modal-input {
    @apply rounded-xl border border-white/15 bg-surface-850 px-3 py-2 text-slate-100 outline-none placeholder:text-muted-500;
  }

  .dm-create-modal-select {
    @apply rounded-xl border border-white/15 bg-surface-850 px-3 py-2 text-slate-100 outline-none;
  }

  .dm-create-modal-recipient-box {
    @apply rounded-xl border border-white/15 bg-surface-850 px-3 py-2;
  }

  .dm-create-modal-chips {
    @apply mb-2 flex flex-wrap gap-1.5;
  }

  .dm-create-modal-chip {
    @apply inline-flex items-center gap-1 rounded-full border border-white/15 bg-white/10 px-2 py-1 text-xs text-slate-100;
  }

  .dm-create-modal-chip-button {
    @apply rounded p-0.5 text-muted-300 hover:bg-white/10 hover:text-slate-100;
  }

  .dm-create-modal-search {
    @apply relative;
  }

  .dm-create-modal-search-input {
    @apply w-full rounded-lg border border-white/10 bg-surface-900 py-2 pl-8 pr-2 text-sm text-slate-100 outline-none placeholder:text-muted-500;
  }

  .dm-create-modal-results {
    @apply mt-2 max-h-44 overflow-auto rounded-lg border border-white/10 bg-surface-900;
  }

  .dm-create-modal-results-copy {
    @apply px-3 py-2 text-xs text-muted-400;
  }

  .dm-create-modal-result {
    @apply flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-100 transition hover:bg-white/10;
  }

  .dm-create-modal-result-avatar {
    @apply h-7 w-7 shrink-0 overflow-hidden rounded-full bg-surface-800;
  }

  .dm-create-modal-result-avatar-image {
    @apply h-full w-full object-cover;
  }

  .dm-create-modal-result-content {
    @apply min-w-0;
  }

  .dm-create-modal-result-name {
    @apply truncate text-sm;
  }

  .dm-create-modal-result-email {
    @apply truncate text-xs text-muted-400;
  }

  .dm-create-modal-actions {
    @apply mt-5 flex items-center justify-end gap-2;
  }

  .dm-create-modal-button {
    @apply rounded-xl px-4 py-2 text-sm transition;
  }

  .dm-create-modal-button-secondary {
    @apply border border-white/15 text-muted-200 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60;
  }

  .dm-create-modal-button-primary {
    @apply bg-accent-500 font-semibold text-white hover:bg-accent-400 disabled:cursor-not-allowed disabled:opacity-70;
  }
</style>
