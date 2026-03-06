import { writable } from 'svelte/store';
import type { Server } from '../../types/gateway';

export const servers = writable<Server[]>([]);
