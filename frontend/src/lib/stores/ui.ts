import { writable } from 'svelte/store';
import type { Server, Channel } from '../../types/gateway';

export const activeServer = writable<Server | null>(null);
export const activeChannel = writable<Channel | null>(null);
