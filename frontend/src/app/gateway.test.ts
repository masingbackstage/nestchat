import { describe, expect, it, vi } from 'vitest';
import { createGatewayEventHandler, type GatewayEventHandlerDeps } from './gateway';

function createDeps(): GatewayEventHandlerDeps {
  return {
    toApiAbsoluteUrl: vi.fn((value: string | null | undefined) => value ?? null),
    pushToast: vi.fn(() => 1),
    ensureServerMembers: vi.fn().mockResolvedValue(undefined),
    updateServerMemberPresence: vi.fn(() => true),
    addMessage: vi.fn(),
    incrementUnreadCount: vi.fn(),
    softDeleteMessage: vi.fn(),
    updateMessage: vi.fn(),
    addDMMessage: vi.fn(),
    updateDMMessage: vi.fn(),
    softDeleteDMMessage: vi.fn(),
    updateDMConversationPreview: vi.fn(),
    incrementDMUnread: vi.fn(),
    clearDMUnread: vi.fn(),
    getActiveChannelUuid: vi.fn(() => null),
    getActiveDMConversationUuid: vi.fn(() => null),
  };
}

describe('createGatewayEventHandler', () => {
  it('shows a toast for gateway validation errors', () => {
    const deps = createDeps();
    const handler = createGatewayEventHandler(deps);

    handler({
      module: 'system',
      action: 'error',
      payload: {
        code: 'validation_error',
        detail: 'Blank message',
      },
    });

    expect(deps.pushToast).toHaveBeenCalledWith({
      type: 'error',
      message: 'Blank message',
    });
  });

  it('shows a toast for string gateway errors', () => {
    const deps = createDeps();
    const handler = createGatewayEventHandler(deps);

    handler({
      module: 'system',
      action: 'error',
      payload: 'Unexpected DM error',
    });

    expect(deps.pushToast).toHaveBeenCalledWith({
      type: 'error',
      message: 'Unexpected DM error',
    });
  });
});
