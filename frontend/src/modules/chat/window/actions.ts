import { tick } from 'svelte';
import { sendDeleteMessage, sendEditMessage, sendToggleReaction } from '../../../lib/socket';
import { pushToast } from '../../../lib/stores/toast';
import type {
  ActiveWindowContext,
  EditMessageEventDetail,
  ManageableMessage,
  MessageActionState,
  MessageEventDetail,
  ReactionEventDetail,
} from './types';

export function createMessageActionState(): MessageActionState {
  return {
    busyMessageActions: new Set<string>(),
    pendingDeleteMessageUuid: null,
    isDeleteConfirmSubmitting: false,
  };
}

export function canManageMessage(
  message: ManageableMessage,
  activeServer: ActiveWindowContext['activeServer'],
  currentUserUuid: string | null,
): boolean {
  if (message.pending) {
    return false;
  }

  const isOwner = Boolean(activeServer?.isOwner ?? activeServer?.is_owner ?? false);
  const isAuthor = Boolean(currentUserUuid && message.author_uuid === currentUserUuid);
  return isOwner || isAuthor;
}

export function isMessageBusy(state: MessageActionState, messageUuid: string): boolean {
  return state.busyMessageActions.has(messageUuid);
}

export function markBusy(
  state: MessageActionState,
  messageUuid: string,
  busy: boolean,
): MessageActionState {
  const nextBusy = new Set(state.busyMessageActions);
  if (busy) {
    nextBusy.add(messageUuid);
  } else {
    nextBusy.delete(messageUuid);
  }

  return {
    ...state,
    busyMessageActions: nextBusy,
  };
}

export async function handleEditMessage(
  state: MessageActionState,
  detail: EditMessageEventDetail,
): Promise<MessageActionState> {
  let nextState = markBusy(state, detail.messageUuid, true);
  const sent = sendEditMessage(detail.messageUuid, detail.content);
  if (!sent) {
    pushToast({ type: 'error', message: 'Gateway connection is unavailable.' });
  }

  await tick();
  nextState = markBusy(nextState, detail.messageUuid, false);
  return nextState;
}

export function handleToggleReaction(detail: ReactionEventDetail): void {
  const sent = sendToggleReaction(detail.messageUuid, detail.emoji);
  if (!sent) {
    pushToast({ type: 'error', message: 'Gateway connection is unavailable.' });
  }
}

export function openDeleteConfirmation(
  state: MessageActionState,
  detail: MessageEventDetail,
): MessageActionState {
  return {
    ...state,
    pendingDeleteMessageUuid: detail.messageUuid,
  };
}

export function cancelDeleteConfirmation(state: MessageActionState): MessageActionState {
  if (state.isDeleteConfirmSubmitting) {
    return state;
  }

  return {
    ...state,
    pendingDeleteMessageUuid: null,
  };
}

export function shouldCloseDeleteOverlay(event: MouseEvent): boolean {
  return event.target === event.currentTarget;
}

export async function confirmDeleteMessage(state: MessageActionState): Promise<MessageActionState> {
  if (!state.pendingDeleteMessageUuid) {
    return state;
  }

  const messageUuid = state.pendingDeleteMessageUuid;
  let nextState = {
    ...markBusy(state, messageUuid, true),
    isDeleteConfirmSubmitting: true,
  };

  const sent = sendDeleteMessage(messageUuid);
  if (!sent) {
    pushToast({ type: 'error', message: 'Gateway connection is unavailable.' });
    return {
      ...markBusy(nextState, messageUuid, false),
      isDeleteConfirmSubmitting: false,
    };
  }

  await tick();
  nextState = markBusy(nextState, messageUuid, false);
  return {
    ...nextState,
    pendingDeleteMessageUuid: null,
    isDeleteConfirmSubmitting: false,
  };
}
