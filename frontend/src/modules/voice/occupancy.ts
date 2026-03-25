import { writable } from 'svelte/store';
import type { Server, VoiceMembersChangedPayload, VoiceOccupant } from '../../types/gateway';

export const voiceOccupantsByChannel = writable<Record<string, VoiceOccupant[]>>({});

function normalizeOccupant(occupant: VoiceOccupant): VoiceOccupant {
  const userUuid = occupant.userUuid ?? occupant.user_uuid ?? '';
  const displayName = occupant.displayName ?? occupant.display_name ?? 'Unknown user';
  const avatarUrl = occupant.avatarUrl ?? occupant.avatar_url ?? null;
  const isMuted = Boolean(occupant.isMuted ?? occupant.is_muted ?? false);
  const isSpeaking = Boolean(occupant.isSpeaking ?? occupant.is_speaking ?? false);
  const audioLevel = Number(occupant.audioLevel ?? occupant.audio_level ?? 0);

  return {
    userUuid,
    user_uuid: userUuid,
    displayName,
    display_name: displayName,
    avatarUrl,
    avatar_url: avatarUrl,
    isMuted,
    is_muted: isMuted,
    isSpeaking,
    is_speaking: isSpeaking,
    audioLevel,
    audio_level: audioLevel,
  };
}

export function hydrateVoiceOccupants(servers: Server[]): void {
  const nextState: Record<string, VoiceOccupant[]> = {};

  for (const server of servers) {
    for (const channel of server.channels ?? []) {
      nextState[channel.uuid] = (channel.voiceOccupants ?? channel.voice_occupants ?? []).map(
        normalizeOccupant,
      );
    }
  }

  voiceOccupantsByChannel.set(nextState);
}

export function applyVoiceMembersChanged(payload: VoiceMembersChangedPayload): void {
  const channelUuid = payload.channelUuid ?? payload.channel_uuid;
  if (!channelUuid) {
    return;
  }

  setVoiceOccupants(channelUuid, payload.occupants ?? []);
}

export function setVoiceOccupants(channelUuid: string, occupants: VoiceOccupant[]): void {
  voiceOccupantsByChannel.update((current) => ({
    ...current,
    [channelUuid]: occupants.map(normalizeOccupant),
  }));
}

export function setVoiceSpeakingState(
  channelUuid: string,
  speakingByUserUuid: Record<string, number>,
): void {
  voiceOccupantsByChannel.update((current) => {
    const occupants = current[channelUuid] ?? [];
    if (occupants.length === 0) {
      return current;
    }

    return {
      ...current,
      [channelUuid]: occupants.map((occupant) => {
        const userUuid = occupant.userUuid ?? occupant.user_uuid ?? '';
        const audioLevel = speakingByUserUuid[userUuid] ?? 0;
        const isSpeaking = audioLevel > 0;
        return {
          ...occupant,
          isSpeaking,
          is_speaking: isSpeaking,
          audioLevel,
          audio_level: audioLevel,
        };
      }),
    };
  });
}

export function setVoiceMutedState(channelUuid: string, mutedByUserUuid: Record<string, boolean>): void {
  voiceOccupantsByChannel.update((current) => {
    const occupants = current[channelUuid] ?? [];
    if (occupants.length === 0) {
      return current;
    }

    return {
      ...current,
      [channelUuid]: occupants.map((occupant) => {
        const userUuid = occupant.userUuid ?? occupant.user_uuid ?? '';
        const isMuted = Boolean(mutedByUserUuid[userUuid]);
        return {
          ...occupant,
          isMuted,
          is_muted: isMuted,
        };
      }),
    };
  });
}

export function resetVoiceOccupants(): void {
  voiceOccupantsByChannel.set({});
}
