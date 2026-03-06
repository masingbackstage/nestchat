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
