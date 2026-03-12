import { tick } from 'svelte';
import { loadNewerMessages, loadOlderMessages } from '../messages';
import { isNearBottom } from './utils';
import type { ViewportState, WindowChannelQueryState } from './types';

type SyncViewportArgs = {
  state: ViewportState;
  activeChannelUuid: string | null;
  currentMessagesLength: number;
  messagesContainer: HTMLDivElement | null;
};

type MaybeLoadArgs = {
  state: ViewportState;
  activeChannelUuid: string | null;
  currentChannelQuery: WindowChannelQueryState | null;
  messagesContainer: HTMLDivElement | null;
};

type ScrollToBottomArgs = {
  state: ViewportState;
  activeChannelUuid: string | null;
  channelUuid: string;
  messagesContainer: HTMLDivElement | null;
};

type JumpToLatestArgs = {
  state: ViewportState;
  activeChannelUuid: string | null;
  currentChannelQuery: WindowChannelQueryState | null;
  messagesContainer: HTMLDivElement | null;
};

export function createViewportState(): ViewportState {
  return {
    loadingOlderFromScroll: false,
    loadingNewerFromScroll: false,
    lastAutoScrolledChannelUuid: null,
    previousChannelUuid: null,
    previousMessageCount: 0,
    isViewportNearBottom: true,
    forceScrollToBottom: false,
    isPositioningAfterViewSwitch: false,
  };
}

export function syncViewportState({
  state,
  activeChannelUuid,
  currentMessagesLength,
  messagesContainer,
}: SyncViewportArgs): { state: ViewportState; shouldScrollToBottom: boolean } {
  if (!activeChannelUuid || !messagesContainer) {
    if (
      state.previousChannelUuid === null &&
      state.previousMessageCount === 0 &&
      state.isViewportNearBottom
    ) {
      return {
        state,
        shouldScrollToBottom: false,
      };
    }

    return {
      state: {
        ...state,
        previousChannelUuid: null,
        previousMessageCount: 0,
        isViewportNearBottom: true,
      },
      shouldScrollToBottom: false,
    };
  }

  const channelChanged = state.previousChannelUuid !== activeChannelUuid;
  const hadMoreMessages = currentMessagesLength > state.previousMessageCount;
  const nearBottom = isNearBottom(messagesContainer);
  const shouldScrollToBottom = !channelChanged && hadMoreMessages && nearBottom;

  const nextState: ViewportState = {
    ...state,
    previousChannelUuid: activeChannelUuid,
    previousMessageCount: currentMessagesLength,
    isViewportNearBottom: nearBottom,
    isPositioningAfterViewSwitch: channelChanged ? true : state.isPositioningAfterViewSwitch,
    forceScrollToBottom: channelChanged ? true : state.forceScrollToBottom,
  };

  if (
    nextState.previousChannelUuid === state.previousChannelUuid &&
    nextState.previousMessageCount === state.previousMessageCount &&
    nextState.isViewportNearBottom === state.isViewportNearBottom &&
    nextState.isPositioningAfterViewSwitch === state.isPositioningAfterViewSwitch &&
    nextState.forceScrollToBottom === state.forceScrollToBottom
  ) {
    return { state, shouldScrollToBottom };
  }

  return { state: nextState, shouldScrollToBottom };
}

export async function scrollToBottomForChannel({
  state,
  activeChannelUuid,
  channelUuid,
  messagesContainer,
}: ScrollToBottomArgs): Promise<ViewportState> {
  await tick();
  if (!messagesContainer || activeChannelUuid !== channelUuid) {
    return state;
  }

  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  return {
    ...state,
    lastAutoScrolledChannelUuid: channelUuid,
    isViewportNearBottom: true,
    isPositioningAfterViewSwitch: false,
  };
}

export async function maybeLoadOlderMessages({
  state,
  activeChannelUuid,
  currentChannelQuery,
  messagesContainer,
}: MaybeLoadArgs): Promise<ViewportState> {
  if (
    !activeChannelUuid ||
    !messagesContainer ||
    state.isPositioningAfterViewSwitch ||
    state.loadingOlderFromScroll ||
    !currentChannelQuery?.hasMoreOlder ||
    !currentChannelQuery.nextBefore ||
    currentChannelQuery.isLoadingOlder
  ) {
    return state;
  }

  if (messagesContainer.scrollTop > 40) {
    return state;
  }

  const nextState = {
    ...state,
    loadingOlderFromScroll: true,
  };
  const previousScrollHeight = messagesContainer.scrollHeight;
  await loadOlderMessages(activeChannelUuid);
  await tick();

  if (!messagesContainer) {
    return {
      ...nextState,
      loadingOlderFromScroll: false,
    };
  }

  const delta = messagesContainer.scrollHeight - previousScrollHeight;
  messagesContainer.scrollTop += Math.max(0, delta);

  return {
    ...nextState,
    loadingOlderFromScroll: false,
    isViewportNearBottom: isNearBottom(messagesContainer),
  };
}

export async function maybeLoadNewerMessages({
  state,
  activeChannelUuid,
  currentChannelQuery,
  messagesContainer,
}: MaybeLoadArgs): Promise<ViewportState> {
  if (
    !activeChannelUuid ||
    !messagesContainer ||
    state.isPositioningAfterViewSwitch ||
    state.loadingNewerFromScroll ||
    !currentChannelQuery?.hasMoreNewer ||
    !currentChannelQuery.nextAfter ||
    currentChannelQuery.isLoadingNewer
  ) {
    return state;
  }

  if (!isNearBottom(messagesContainer)) {
    return state;
  }

  const nextState = {
    ...state,
    loadingNewerFromScroll: true,
  };
  const previousFromBottom =
    messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight;

  await loadNewerMessages(activeChannelUuid);
  await tick();

  if (!messagesContainer) {
    return {
      ...nextState,
      loadingNewerFromScroll: false,
    };
  }

  messagesContainer.scrollTop = Math.max(
    0,
    messagesContainer.scrollHeight - messagesContainer.clientHeight - previousFromBottom,
  );

  return {
    ...nextState,
    loadingNewerFromScroll: false,
    isViewportNearBottom: isNearBottom(messagesContainer),
  };
}

export async function jumpToLatest({
  state,
  activeChannelUuid,
  currentChannelQuery,
  messagesContainer,
}: JumpToLatestArgs): Promise<ViewportState> {
  if (!activeChannelUuid || !messagesContainer) {
    return state;
  }

  if (currentChannelQuery?.hasMoreNewer && !currentChannelQuery.isLoadingNewer) {
    await loadNewerMessages(activeChannelUuid);
    await tick();
  }

  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  return {
    ...state,
    isViewportNearBottom: true,
  };
}
