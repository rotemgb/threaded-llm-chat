import type { ModelOption } from "../models/modelOption";
import type { Summary } from "../models/summaryViewModel";

export type Thread = {
  id: number;
  title: string | null;
};

export type Message = {
  id: number;
  role: string;
  content: string;
};

export type SendMessageResult = {
  user_message: Message;
  assistant_message: Message;
  model_used: string;
};

export interface ChatApiPort {
  listThreads(): Promise<Thread[]>;
  createThread(payload: { system_prompt: string; title: string | null }): Promise<Thread>;
  listMessages(threadId: number): Promise<Message[]>;
  sendMessage(payload: {
    threadId: number;
    content: string;
    sender: string;
    model: string | null;
  }): Promise<SendMessageResult>;
  listSummaries(threadId: number): Promise<Summary[]>;
  listModels(): Promise<ModelOption[]>;
}
