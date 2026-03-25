import { writable } from 'svelte/store';
import type { Channel, DMConversation, Server } from '../../types/gateway';
import type { StoredDMUI } from '../../modules/dm/storage';

export const activeServer = writable<Server | null>(null);
export const activeChannel = writable<Channel | null>(null);
export const activeDMConversation = writable<DMConversation | null>(null);

export type ResolvedActiveView = {
  activeServer: Server | null;
  activeChannel: Channel | null;
  isDMView: boolean;
};

export function resolveStoredActiveView(
  availableServers: Server[],
  uiCache: Pick<StoredDMUI, 'activeServerUuid' | 'activeChannelUuid' | 'isDMView'>,
): ResolvedActiveView {
  if (uiCache.isDMView) {
    return {
      activeServer: null,
      activeChannel: null,
      isDMView: true,
    };
  }

  const fallbackServer = availableServers[0] ?? null;
  if (!fallbackServer) {
    return {
      activeServer: null,
      activeChannel: null,
      isDMView: false,
    };
  }

  const restoredServer =
    availableServers.find((server) => server.uuid === uiCache.activeServerUuid) ?? fallbackServer;
  const restoredChannel =
    restoredServer.channels.find((channel) => channel.uuid === uiCache.activeChannelUuid) ??
    restoredServer.channels[0] ??
    null;

  return {
    activeServer: restoredServer,
    activeChannel: restoredChannel,
    isDMView: false,
  };
}
