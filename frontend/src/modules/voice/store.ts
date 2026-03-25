import { writable, get } from 'svelte/store';
import {
  AudioPresets,
  type LocalAudioTrack,
  type Participant,
  Room,
  RoomEvent,
  Track,
  createLocalAudioTrack,
  type RemoteParticipant,
  type RemoteTrack,
  type RemoteTrackPublication,
} from 'livekit-client';
import { getCurrentUserUuid } from '../../lib/auth';
import { ensureServerMembers, membersByServer } from '../servers/members/store';
import { fetchVoiceToken } from './api';
import { setVoiceMutedState, setVoiceOccupants, setVoiceSpeakingState } from './occupancy';
import {
  clampVoiceThreshold,
  DEFAULT_VOICE_HANGOVER_MS,
  nextVoiceGateState,
  type VoiceGateState,
} from './gate';
import { loadVoiceThreshold, saveVoiceThreshold } from './storage';

type VoiceState = {
  status: 'idle' | 'connecting' | 'connected' | 'error';
  serverUuid: string | null;
  channelUuid: string | null;
  roomName: string | null;
  participants: number;
  muted: boolean;
  error: string | null;
  channelName: string | null;
  inputLevel: number;
  gateOpen: boolean;
  threshold: number;
  hangoverMs: number;
};

type VoiceSettings = {
  threshold: number;
  hangoverMs: number;
};

const initial: VoiceState = {
  status: 'idle',
  serverUuid: null,
  channelUuid: null,
  roomName: null,
  participants: 0,
  muted: false,
  error: null,
  channelName: null,
  inputLevel: 0,
  gateOpen: false,
  threshold: loadVoiceThreshold(),
  hangoverMs: DEFAULT_VOICE_HANGOVER_MS,
};

type LastJoinTarget = {
  serverUuid: string;
  channelUuid: string;
  channelName: string;
};

type RemoteAudioGraph = {
  context: AudioContext;
  source: MediaStreamAudioSourceNode;
  splitter: ChannelSplitterNode;
  merger: ChannelMergerNode;
  gain: GainNode;
};

type LocalAudioGraph = {
  context: AudioContext;
  analysisStream: MediaStream;
  source: MediaStreamAudioSourceNode;
  analyser: AnalyserNode;
  meterData: Float32Array<ArrayBuffer>;
  rafId: number | null;
  gate: VoiceGateState;
};

let lastJoinTarget: LastJoinTarget | null = null;
let voiceSettings: VoiceSettings = {
  threshold: initial.threshold,
  hangoverMs: initial.hangoverMs,
};

export const voiceState = writable<VoiceState>(initial);

let room: Room | null = null;
let localAudioTrack: LocalAudioTrack | null = null;
let localAudioGraph: LocalAudioGraph | null = null;

const remoteAudioGraphs = new Map<string, RemoteAudioGraph>();

const ignorePromiseRejection = (): undefined => undefined;

function setError(message: string): void {
  voiceState.update((s) => ({ ...s, status: 'error', error: message }));
}

function updateVoiceDiagnostics(inputLevel: number, gateOpen: boolean): void {
  voiceState.update((s) => {
    if (s.inputLevel === inputLevel && s.gateOpen === gateOpen) {
      return s;
    }

    return {
      ...s,
      inputLevel,
      gateOpen,
    };
  });
}

function resolveVoiceOccupant(
  userUuid: string,
  serverUuid: string,
  fallbackLabel: string,
): { user_uuid: string; display_name: string; avatar_url: string | null } {
  const groups = get(membersByServer)[serverUuid] ?? [];
  for (const group of groups) {
    const member = group.members.find((item) => item.uuid === userUuid);
    if (member) {
      return {
        user_uuid: member.uuid,
        display_name: member.displayName,
        avatar_url: member.avatarUrl,
      };
    }
  }

  return {
    user_uuid: userUuid,
    display_name: fallbackLabel,
    avatar_url: null,
  };
}

function syncCurrentRoomOccupants(r: Room): void {
  const current = get(voiceState);
  if (!current.serverUuid || !current.channelUuid) {
    return;
  }

  const selfUuid = getCurrentUserUuid();
  const occupants: { user_uuid: string; display_name: string; avatar_url: string | null }[] = [];

  if (selfUuid) {
    occupants.push(resolveVoiceOccupant(selfUuid, current.serverUuid, 'You'));
  }

  for (const participant of r.remoteParticipants.values()) {
    const participantUuid = participant.identity;
    if (!participantUuid || participantUuid === selfUuid) {
      continue;
    }

    occupants.push(resolveVoiceOccupant(participantUuid, current.serverUuid, 'Connected user'));
  }

  setVoiceOccupants(current.channelUuid, occupants);
  syncCurrentRoomMutedState(r);
  syncCurrentRoomActiveSpeakers(r);
}

function syncCurrentRoomMutedState(r: Room): void {
  const channelUuid = get(voiceState).channelUuid;
  if (!channelUuid) {
    return;
  }

  const selfUuid = getCurrentUserUuid();
  const mutedByUserUuid: Record<string, boolean> = {};

  if (selfUuid) {
    mutedByUserUuid[selfUuid] = get(voiceState).muted || !r.localParticipant.isMicrophoneEnabled;
  }

  for (const participant of r.remoteParticipants.values()) {
    const participantUuid = participant.identity;
    if (!participantUuid || participantUuid === selfUuid) {
      continue;
    }

    mutedByUserUuid[participantUuid] = !participant.isMicrophoneEnabled;
  }

  setVoiceMutedState(channelUuid, mutedByUserUuid);
}

function syncCurrentRoomActiveSpeakers(r: Room): void {
  const channelUuid = get(voiceState).channelUuid;
  if (!channelUuid) {
    return;
  }

  const selfUuid = getCurrentUserUuid();
  const speakingByUserUuid: Record<string, number> = {};

  for (const participant of r.activeSpeakers as Participant[]) {
    const participantUuid =
      participant === r.localParticipant ? selfUuid : ('identity' in participant ? participant.identity : null);
    if (!participantUuid) {
      continue;
    }
    speakingByUserUuid[participantUuid] = participant.audioLevel ?? 1;
  }

  setVoiceSpeakingState(channelUuid, speakingByUserUuid);
}

function syncLocalTransmissionEnabled(): void {
  if (!localAudioTrack) {
    return;
  }

  const manualMute = get(voiceState).muted;
  const gateOpen = localAudioGraph?.gate.isOpen ?? false;
  localAudioTrack.mediaStreamTrack.enabled = !manualMute && gateOpen;
}

function computeInputLevel(analyser: AnalyserNode, meterData: Float32Array<ArrayBuffer>): number {
  analyser.getFloatTimeDomainData(meterData);

  let sum = 0;
  for (const sample of meterData) {
    sum += sample * sample;
  }

  return Math.min(1, Math.sqrt(sum / meterData.length));
}

function startVoiceMeter(graph: LocalAudioGraph): void {
  const tick = (): void => {
    if (!localAudioGraph || localAudioGraph !== graph) {
      return;
    }

    const inputLevel = computeInputLevel(graph.analyser, graph.meterData);
    const nowMs = performance.now();
    const nextGate = nextVoiceGateState(graph.gate, {
      level: inputLevel,
      threshold: voiceSettings.threshold,
      nowMs,
      hangoverMs: voiceSettings.hangoverMs,
    });

    graph.gate = nextGate;
    syncLocalTransmissionEnabled();
    updateVoiceDiagnostics(inputLevel, nextGate.isOpen && !get(voiceState).muted);
    graph.rafId = window.setTimeout(tick, 50);
  };

  tick();
}

async function createLocalAudioAnalysisGraph(track: LocalAudioTrack): Promise<void> {
  if (typeof window === 'undefined' || typeof AudioContext === 'undefined') {
    throw new Error('Web Audio is not available in this environment.');
  }

  const context = new AudioContext();
  const analysisTrack = track.mediaStreamTrack.clone();
  const analysisStream = new MediaStream([analysisTrack]);
  const source = context.createMediaStreamSource(analysisStream);
  const analyser = context.createAnalyser();
  const meterData = new Float32Array(new ArrayBuffer(2048 * Float32Array.BYTES_PER_ELEMENT));

  analyser.fftSize = 2048;
  analyser.smoothingTimeConstant = 0.1;

  source.connect(analyser);

  localAudioGraph = {
    context,
    analysisStream,
    source,
    analyser,
    meterData,
    rafId: null,
    gate: {
      isOpen: false,
      lastVoiceAtMs: null,
    },
  };

  startVoiceMeter(localAudioGraph);
  await context.resume();
}

async function cleanupLocalAudio(): Promise<void> {
  if (localAudioGraph) {
    if (localAudioGraph.rafId !== null) {
      window.clearTimeout(localAudioGraph.rafId);
    }

    localAudioGraph.source.disconnect();
    localAudioGraph.analyser.disconnect();
    localAudioGraph.analysisStream.getTracks().forEach((track) => track.stop());
    await localAudioGraph.context.close().catch(ignorePromiseRejection);
    localAudioGraph = null;
  }

  if (localAudioTrack) {
    localAudioTrack.stop();
    localAudioTrack = null;
  }

  updateVoiceDiagnostics(0, false);
}

function getPublicationSid(publication: RemoteTrackPublication): string {
  return publication.trackSid;
}

function attachRemoteAudio(track: RemoteTrack, publication: RemoteTrackPublication): void {
  if (track.kind !== Track.Kind.Audio) {
    return;
  }

  if (typeof window === 'undefined' || typeof AudioContext === 'undefined') {
    return;
  }

  const sid = getPublicationSid(publication);
  if (!sid || remoteAudioGraphs.has(sid)) {
    return;
  }

  const mediaStreamTrack = track.mediaStreamTrack;
  if (!mediaStreamTrack) {
    return;
  }

  const stream = new MediaStream([mediaStreamTrack]);
  const context = new AudioContext();

  const source = context.createMediaStreamSource(stream);
  const splitter = context.createChannelSplitter(1);
  const merger = context.createChannelMerger(2);
  const gain = context.createGain();

  gain.gain.value = 1.0;

  source.connect(splitter);
  splitter.connect(merger, 0, 0);
  splitter.connect(merger, 0, 1);
  merger.connect(gain);
  gain.connect(context.destination);

  remoteAudioGraphs.set(sid, { context, source, splitter, merger, gain });

  void context.resume().catch(ignorePromiseRejection);
}

function detachRemoteAudio(publication: RemoteTrackPublication): void {
  const sid = getPublicationSid(publication);
  const graph = remoteAudioGraphs.get(sid);
  if (!graph) {
    return;
  }

  graph.source.disconnect();
  graph.splitter.disconnect();
  graph.merger.disconnect();
  graph.gain.disconnect();
  void graph.context.close().catch(ignorePromiseRejection);

  remoteAudioGraphs.delete(sid);
}

function detachParticipantRemoteAudio(participant: RemoteParticipant): void {
  for (const publication of participant.trackPublications.values()) {
    detachRemoteAudio(publication);
  }
}

function cleanupRemoteAudio(): void {
  for (const graph of remoteAudioGraphs.values()) {
    graph.source.disconnect();
    graph.splitter.disconnect();
    graph.merger.disconnect();
    graph.gain.disconnect();
    void graph.context.close().catch(ignorePromiseRejection);
  }

  remoteAudioGraphs.clear();
}

function bindRoomEvents(r: Room): void {
  const updateParticipants = (): void => {
    voiceState.update((s) => ({
      ...s,
      participants: r.numParticipants,
    }));
    syncCurrentRoomOccupants(r);
  };

  r.on(RoomEvent.ParticipantConnected, updateParticipants);

  r.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
    detachParticipantRemoteAudio(participant);
    updateParticipants();
  });

  r.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: RemoteTrackPublication) => {
    attachRemoteAudio(track, publication);
  });

  r.on(RoomEvent.TrackUnsubscribed, (_track: RemoteTrack, publication: RemoteTrackPublication) => {
    detachRemoteAudio(publication);
  });

  r.on(RoomEvent.ActiveSpeakersChanged, () => {
    syncCurrentRoomActiveSpeakers(r);
  });

  r.on(RoomEvent.TrackMuted, () => {
    syncCurrentRoomMutedState(r);
  });

  r.on(RoomEvent.TrackUnmuted, () => {
    syncCurrentRoomMutedState(r);
  });

  r.on(RoomEvent.Disconnected, () => {
    cleanupRemoteAudio();
    voiceState.set({ ...initial });
  });
}

export async function joinVoiceCall(
  serverUuid: string,
  channelUuid: string,
  channelName: string,
): Promise<void> {
  lastJoinTarget = { serverUuid, channelUuid, channelName };

  const current = get(voiceState);
  if (current.status === 'connecting') {
    return;
  }

  if (
    current.status === 'connected' &&
    current.serverUuid === serverUuid &&
    current.channelUuid === channelUuid
  ) {
    return;
  }

  await leaveVoiceCall();

  voiceState.set({
    ...initial,
    status: 'connecting',
    serverUuid,
    channelUuid,
    channelName,
  });

  try {
    const tokenData = await fetchVoiceToken(serverUuid, channelUuid);
    if (!tokenData.livekitPublicUrl) {
      throw new Error('Missing livekitPublicUrl in token response.');
    }

    room = new Room();
    bindRoomEvents(room);

    await room.connect(tokenData.livekitPublicUrl, tokenData.token);
    void ensureServerMembers(serverUuid)
      .then(() => {
        if (room) {
          syncCurrentRoomOccupants(room);
        }
      })
      .catch(ignorePromiseRejection);

    for (const participant of room.remoteParticipants.values()) {
      for (const publication of participant.trackPublications.values()) {
        const publicationTrack = publication.track;
        if (publicationTrack && publicationTrack.kind === Track.Kind.Audio) {
          attachRemoteAudio(publicationTrack as RemoteTrack, publication);
        }
      }
    }

    localAudioTrack = await createLocalAudioTrack({
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      voiceIsolation: true,
      channelCount: 1,
    });
    localAudioTrack.source = Track.Source.Microphone;
    await createLocalAudioAnalysisGraph(localAudioTrack);
    syncLocalTransmissionEnabled();

    await room.localParticipant.publishTrack(localAudioTrack, {
      audioPreset: AudioPresets.musicHighQuality,
    });

    voiceState.update((s) => ({
      ...s,
      status: 'connected',
      roomName: tokenData.roomName,
      participants: room?.numParticipants ?? 1,
      muted: false,
      error: null,
      threshold: voiceSettings.threshold,
      hangoverMs: voiceSettings.hangoverMs,
    }));
    syncCurrentRoomOccupants(room);
  } catch (err) {
    await leaveVoiceCall();
    setError(err instanceof Error ? err.message : 'Failed to join voice call.');
  }
}

export async function leaveVoiceCall(): Promise<void> {
  const channelUuid = get(voiceState).channelUuid;
  try {
    await cleanupLocalAudio();

    cleanupRemoteAudio();

    if (room) {
      room.disconnect();
      room = null;
    }
  } finally {
    if (channelUuid) {
      setVoiceOccupants(channelUuid, []);
    }
    voiceState.set({ ...initial });
  }
}

export async function toggleMute(): Promise<void> {
  if (!localAudioTrack) {
    return;
  }

  const nextMuted = !get(voiceState).muted;
  voiceState.update((s) => ({ ...s, muted: nextMuted, gateOpen: nextMuted ? false : s.gateOpen }));

  try {
    if (nextMuted) {
      await localAudioTrack.mute();
    } else {
      await localAudioTrack.unmute();
    }
  } catch {
    voiceState.update((s) => ({ ...s, muted: !nextMuted }));
  }

  syncLocalTransmissionEnabled();
  if (room) {
    syncCurrentRoomMutedState(room);
  }
}

export function setVoiceThreshold(value: number): void {
  const threshold = clampVoiceThreshold(value);
  voiceSettings = {
    ...voiceSettings,
    threshold,
  };
  saveVoiceThreshold(threshold);
  voiceState.update((s) => ({
    ...s,
    threshold,
  }));
}

export async function reconnectVoiceCall(): Promise<void> {
  if (!lastJoinTarget) {
    return;
  }

  await joinVoiceCall(
    lastJoinTarget.serverUuid,
    lastJoinTarget.channelUuid,
    lastJoinTarget.channelName,
  );
}
