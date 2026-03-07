import { writable } from 'svelte/store';

export type ToastType = 'success' | 'error';

export type Toast = {
  id: number;
  type: ToastType;
  message: string;
};

export const toasts = writable<Toast[]>([]);

let nextToastId = 1;
const TOAST_AUTO_DISMISS_MS = 4_000;

export function pushToast(input: { type: ToastType; message: string }): number {
  const id = nextToastId++;
  toasts.update((current) => [...current, { id, type: input.type, message: input.message }]);

  setTimeout(() => {
    removeToast(id);
  }, TOAST_AUTO_DISMISS_MS);

  return id;
}

export function removeToast(id: number): void {
  toasts.update((current) => current.filter((toast) => toast.id !== id));
}
