export type Channel = {
  uuid: string;
  name: string;
  channel_type: string;
};

export type Server = {
  uuid: string;
  name: string;
  channels: Channel[];
};

export type Message = {
  uuid: string;
  channel_uuid: string;
  content: string;
  author: string;
  created_at?: string;
};

export type GatewayMessageEvent = {
  module: string;
  action: string;
  payload: unknown;
};
