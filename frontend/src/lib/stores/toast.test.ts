import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { pushToast, removeToast, toasts } from './toast';

describe('toast store', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    toasts.set([]);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('adds and auto-removes toast after timeout', () => {
    pushToast({ type: 'success', message: 'ok' });
    expect(get(toasts)).toHaveLength(1);

    vi.advanceTimersByTime(4_000);
    expect(get(toasts)).toHaveLength(0);
  });

  it('removes toast manually', () => {
    const id = pushToast({ type: 'error', message: 'fail' });
    expect(get(toasts)).toHaveLength(1);

    removeToast(id);
    expect(get(toasts)).toHaveLength(0);
  });
});
