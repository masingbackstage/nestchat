type VoiceCueTone = {
  frequency: number;
  durationMs: number;
  gain: number;
};

type VoiceCue = 'join' | 'leave' | 'mute' | 'unmute';

const cueMap: Record<VoiceCue, VoiceCueTone[]> = {
  join: [
    { frequency: 620, durationMs: 70, gain: 0.032 },
    { frequency: 880, durationMs: 110, gain: 0.036 },
  ],
  leave: [
    { frequency: 740, durationMs: 65, gain: 0.03 },
    { frequency: 520, durationMs: 120, gain: 0.034 },
  ],
  mute: [
    { frequency: 540, durationMs: 70, gain: 0.03 },
    { frequency: 420, durationMs: 90, gain: 0.032 },
  ],
  unmute: [
    { frequency: 480, durationMs: 60, gain: 0.03 },
    { frequency: 700, durationMs: 100, gain: 0.034 },
  ],
};

let soundContext: AudioContext | null = null;
let soundOutput: GainNode | null = null;
const lastCueAtMs = new Map<VoiceCue, number>();
const CUE_COOLDOWN_MS = 140;

function getSoundContext(): AudioContext | null {
  if (typeof window === 'undefined' || typeof AudioContext === 'undefined') {
    return null;
  }

  if (!soundContext) {
    soundContext = new AudioContext();
    soundOutput = soundContext.createGain();
    soundOutput.gain.value = 0.9;
    soundOutput.connect(soundContext.destination);
  }

  return soundContext;
}

async function ensureSoundContext(): Promise<AudioContext | null> {
  const context = getSoundContext();
  if (!context) {
    return null;
  }

  if (context.state === 'suspended') {
    await context.resume();
  }

  return context;
}

export async function playVoiceCue(cue: VoiceCue): Promise<void> {
  const nowMs = Date.now();
  const lastPlayedAtMs = lastCueAtMs.get(cue) ?? 0;
  if (nowMs - lastPlayedAtMs < CUE_COOLDOWN_MS) {
    return;
  }

  const context = await ensureSoundContext();
  if (!context || !soundOutput) {
    return;
  }

  lastCueAtMs.set(cue, nowMs);

  const tones = cueMap[cue];
  let offsetSeconds = 0;

  for (const tone of tones) {
    const oscillator = context.createOscillator();
    const gainNode = context.createGain();
    const startAt = context.currentTime + offsetSeconds;
    const attackSeconds = 0.01;
    const durationSeconds = tone.durationMs / 1000;
    const releaseStart = Math.max(startAt + durationSeconds - 0.045, startAt + attackSeconds);

    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(tone.frequency, startAt);

    gainNode.gain.setValueAtTime(0.0001, startAt);
    gainNode.gain.exponentialRampToValueAtTime(tone.gain, startAt + attackSeconds);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, releaseStart + 0.045);

    oscillator.connect(gainNode);
    gainNode.connect(soundOutput);

    oscillator.start(startAt);
    oscillator.stop(startAt + durationSeconds + 0.05);

    offsetSeconds += durationSeconds * 0.7;
  }
}

export async function primeVoiceSounds(): Promise<void> {
  await ensureSoundContext();
}
