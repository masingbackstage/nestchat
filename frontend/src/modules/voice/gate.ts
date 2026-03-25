export type VoiceGateState = {
  isOpen: boolean;
  lastVoiceAtMs: number | null;
};

export type VoiceGateDecisionInput = {
  level: number;
  threshold: number;
  nowMs: number;
  hangoverMs: number;
};

export const DEFAULT_VOICE_THRESHOLD = 0.025;
export const DEFAULT_VOICE_HANGOVER_MS = 300;
export const MIN_VOICE_THRESHOLD = 0.001;
export const MAX_VOICE_THRESHOLD = 0.1;

export function clampVoiceThreshold(value: number): number {
  if (!Number.isFinite(value)) {
    return DEFAULT_VOICE_THRESHOLD;
  }

  return Math.min(MAX_VOICE_THRESHOLD, Math.max(MIN_VOICE_THRESHOLD, value));
}

export function nextVoiceGateState(
  state: VoiceGateState,
  input: VoiceGateDecisionInput,
): VoiceGateState {
  if (input.level >= input.threshold) {
    return {
      isOpen: true,
      lastVoiceAtMs: input.nowMs,
    };
  }

  if (!state.isOpen || state.lastVoiceAtMs === null) {
    return {
      isOpen: false,
      lastVoiceAtMs: state.lastVoiceAtMs,
    };
  }

  if (input.nowMs - state.lastVoiceAtMs <= input.hangoverMs) {
    return state;
  }

  return {
    isOpen: false,
    lastVoiceAtMs: state.lastVoiceAtMs,
  };
}
