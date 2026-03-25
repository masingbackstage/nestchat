import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import {
  applyVoiceMembersChanged,
  hydrateVoiceOccupants,
  resetVoiceOccupants,
  setVoiceMutedState,
  setVoiceSpeakingState,
  voiceOccupantsByChannel,
} from './occupancy';

describe('voice occupancy store', () => {
  beforeEach(() => {
    resetVoiceOccupants();
  });

  it('hydrates occupants from server payload', () => {
    hydrateVoiceOccupants([
      {
        uuid: 'server-1',
        name: 'Nest',
        channels: [
          {
            uuid: 'voice-1',
            name: 'Lobby',
            channel_type: 'VOICE',
            voice_occupants: [
              {
                user_uuid: 'user-1',
                display_name: 'User 1',
                avatar_url: '/avatars/user-1.png',
              },
            ],
          },
        ],
      },
    ]);

    expect(get(voiceOccupantsByChannel)).toEqual({
      'voice-1': [
        {
          userUuid: 'user-1',
          user_uuid: 'user-1',
          displayName: 'User 1',
          display_name: 'User 1',
          avatarUrl: '/avatars/user-1.png',
          avatar_url: '/avatars/user-1.png',
          isMuted: false,
          is_muted: false,
          isSpeaking: false,
          is_speaking: false,
          audioLevel: 0,
          audio_level: 0,
        },
      ],
    });
  });

  it('updates a single channel from gateway payload', () => {
    applyVoiceMembersChanged({
      server_uuid: 'server-1',
      channel_uuid: 'voice-1',
      occupants: [
        {
          user_uuid: 'user-2',
          display_name: 'User 2',
          avatar_url: null,
        },
      ],
      timestamp: new Date().toISOString(),
    });

    expect(get(voiceOccupantsByChannel)['voice-1']).toEqual([
      {
        userUuid: 'user-2',
        user_uuid: 'user-2',
        displayName: 'User 2',
        display_name: 'User 2',
        avatarUrl: null,
        avatar_url: null,
        isMuted: false,
        is_muted: false,
        isSpeaking: false,
        is_speaking: false,
        audioLevel: 0,
        audio_level: 0,
      },
    ]);
  });

  it('marks occupants as speaking for the active channel', () => {
    applyVoiceMembersChanged({
      server_uuid: 'server-1',
      channel_uuid: 'voice-1',
      occupants: [
        {
          user_uuid: 'user-2',
          display_name: 'User 2',
          avatar_url: null,
        },
        {
          user_uuid: 'user-3',
          display_name: 'User 3',
          avatar_url: null,
        },
      ],
      timestamp: new Date().toISOString(),
    });

    setVoiceSpeakingState('voice-1', { 'user-3': 0.42 });

    expect(get(voiceOccupantsByChannel)['voice-1']).toEqual([
      {
        userUuid: 'user-2',
        user_uuid: 'user-2',
        displayName: 'User 2',
        display_name: 'User 2',
        avatarUrl: null,
        avatar_url: null,
        isMuted: false,
        is_muted: false,
        isSpeaking: false,
        is_speaking: false,
        audioLevel: 0,
        audio_level: 0,
      },
      {
        userUuid: 'user-3',
        user_uuid: 'user-3',
        displayName: 'User 3',
        display_name: 'User 3',
        avatarUrl: null,
        avatar_url: null,
        isMuted: false,
        is_muted: false,
        isSpeaking: true,
        is_speaking: true,
        audioLevel: 0.42,
        audio_level: 0.42,
      },
    ]);
  });

  it('marks occupants as muted for the active channel', () => {
    applyVoiceMembersChanged({
      server_uuid: 'server-1',
      channel_uuid: 'voice-1',
      occupants: [
        {
          user_uuid: 'user-2',
          display_name: 'User 2',
          avatar_url: null,
        },
        {
          user_uuid: 'user-3',
          display_name: 'User 3',
          avatar_url: null,
        },
      ],
      timestamp: new Date().toISOString(),
    });

    setVoiceMutedState('voice-1', { 'user-2': true });

    expect(get(voiceOccupantsByChannel)['voice-1']).toEqual([
      {
        userUuid: 'user-2',
        user_uuid: 'user-2',
        displayName: 'User 2',
        display_name: 'User 2',
        avatarUrl: null,
        avatar_url: null,
        isMuted: true,
        is_muted: true,
        isSpeaking: false,
        is_speaking: false,
        audioLevel: 0,
        audio_level: 0,
      },
      {
        userUuid: 'user-3',
        user_uuid: 'user-3',
        displayName: 'User 3',
        display_name: 'User 3',
        avatarUrl: null,
        avatar_url: null,
        isMuted: false,
        is_muted: false,
        isSpeaking: false,
        is_speaking: false,
        audioLevel: 0,
        audio_level: 0,
      },
    ]);
  });
});
