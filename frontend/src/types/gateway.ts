export interface Channel {
  uuid: string;
  name: string;
  channel_type: string;
}

export interface Server {
  uuid: string;
  name: string;
  channels: Channel[];
}

export interface Message {
  uuid: string;
  channel_uuid: string;
  content: string;
  author: string;
  created_at?: string;
}

export interface GatewayMessageEvent {
  module: 'chat' | 'system' | 'presence' | string;
  action: string;
  payload: unknown;
}
