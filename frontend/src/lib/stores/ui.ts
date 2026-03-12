import { writable } from 'svelte/store';
import type { Channel, DMConversation, Server } from '../../types/gateway';

export const activeServer = writable<Server | null>(null);
export const activeChannel = writable<Channel | null>(null);
export const activeDMConversation = writable<DMConversation | null>(null);
