import { describe, expect, it } from 'vitest';
import { resolveStoredActiveView } from './ui';
import type { Server } from '../../types/gateway';

const servers: Server[] = [
  {
    uuid: 'server-1',
    name: 'Alpha',
    channels: [
      { uuid: 'channel-1', name: 'general' },
      { uuid: 'channel-2', name: 'random' },
    ],
  },
  {
    uuid: 'server-2',
    name: 'Beta',
    channels: [{ uuid: 'channel-3', name: 'updates' }],
  },
];

describe('resolveStoredActiveView', () => {
  it('restores the cached server and channel when they still exist', () => {
    const view = resolveStoredActiveView(servers, {
      activeServerUuid: 'server-1',
      activeChannelUuid: 'channel-2',
      isDMView: false,
    });

    expect(view.isDMView).toBe(false);
    expect(view.activeServer?.uuid).toBe('server-1');
    expect(view.activeChannel?.uuid).toBe('channel-2');
  });

  it('restores the DM view without selecting a server', () => {
    const view = resolveStoredActiveView(servers, {
      activeServerUuid: 'server-1',
      activeChannelUuid: 'channel-2',
      isDMView: true,
    });

    expect(view.isDMView).toBe(true);
    expect(view.activeServer).toBeNull();
    expect(view.activeChannel).toBeNull();
  });

  it('falls back to the first available server and channel for stale cache', () => {
    const view = resolveStoredActiveView(servers, {
      activeServerUuid: 'missing-server',
      activeChannelUuid: 'missing-channel',
      isDMView: false,
    });

    expect(view.isDMView).toBe(false);
    expect(view.activeServer?.uuid).toBe('server-1');
    expect(view.activeChannel?.uuid).toBe('channel-1');
  });
});
