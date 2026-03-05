import type { ChatApiPort, SendMessageResult } from "../api/chatApiPort";

export interface ConversationTransport {
  sendMessage(payload: {
    threadId: number;
    content: string;
    sender: string;
    model: string | null;
  }): Promise<SendMessageResult>;
}

export class PollingConversationTransport implements ConversationTransport {
  constructor(private readonly api: ChatApiPort) {}

  async sendMessage(payload: {
    threadId: number;
    content: string;
    sender: string;
    model: string | null;
  }): Promise<SendMessageResult> {
    return this.api.sendMessage(payload);
  }
}
