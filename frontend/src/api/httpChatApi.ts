import type { ChatApiPort, Message, SendMessageResult, Thread } from "./chatApiPort";
import type { ModelOption } from "../models/modelOption";
import type { Summary } from "../models/summaryViewModel";
import { toModelOptions } from "../models/modelOption";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.toString() || "http://localhost:8000";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export class HttpChatApi implements ChatApiPort {
  async listThreads(): Promise<Thread[]> {
    return api<Thread[]>("/threads");
  }

  async createThread(payload: {
    system_prompt: string;
    title: string | null;
  }): Promise<Thread> {
    return api<Thread>("/threads", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async listMessages(threadId: number): Promise<Message[]> {
    return api<Message[]>(`/threads/${threadId}/messages?limit=200`);
  }

  async sendMessage(payload: {
    threadId: number;
    content: string;
    sender: string;
    model: string | null;
  }): Promise<SendMessageResult> {
    return api<SendMessageResult>(`/threads/${payload.threadId}/messages`, {
      method: "POST",
      body: JSON.stringify({
        content: payload.content,
        sender: payload.sender,
        model: payload.model,
      }),
    });
  }

  async listSummaries(threadId: number): Promise<Summary[]> {
    return api<Summary[]>(`/threads/${threadId}/summaries`);
  }

  async listModels(): Promise<ModelOption[]> {
    const keys = await api<string[]>("/health/models");
    return toModelOptions(keys);
  }
}
