import { authFetch } from '../../lib/auth';
import { getApiBaseUrl } from '../../lib/url';

export type VoiceTokenResponse = {
  token: string;
  livekitPublicUrl: string;
  roomName: string;
  identity: string;
  expiresIn: number;
};

export async function fetchVoiceToken(
  serverUuid: string,
  channelUuid: string,
): Promise<VoiceTokenResponse> {
  const response = await authFetch(`${getApiBaseUrl()}/servers/${serverUuid}/voice-token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel_uuid: channelUuid }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Voice token request failed: HTTP ${response.status} ${text}`);
  }

  return (await response.json()) as VoiceTokenResponse;
}
