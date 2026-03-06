import { useCallback, useEffect, useMemo, useState } from "react";

import type { ChatApiPort, Message, Thread } from "../api/chatApiPort";
import type { ModelOption } from "../models/modelOption";
import { selectLatestSummaryText, type Summary } from "../models/summaryViewModel";
import {
  PollingConversationTransport,
  type ConversationTransport,
} from "../transport/conversationTransport";

export function useChatStore(api: ChatApiPort) {
  const transport: ConversationTransport = useMemo(
    () => new PollingConversationTransport(api),
    [api]
  );

  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [latestSummary, setLatestSummary] = useState<string | null>(null);
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState<string>("");
  const [availableModels, setAvailableModels] = useState<ModelOption[]>([]);
  const [modelLoadError, setModelLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadThreads = useCallback(async () => {
    const data = await api.listThreads();
    setThreads(data);
    setActiveThreadId((prev) => prev ?? data[0]?.id ?? null);
  }, [api]);

  const loadMessages = useCallback(
    async (threadId: number) => {
      const data = await api.listMessages(threadId);
      setMessages(data);
    },
    [api]
  );

  const loadSummaries = useCallback(
    async (threadId: number) => {
      const data: Summary[] = await api.listSummaries(threadId);
      setSummaries(data);
      setLatestSummary(selectLatestSummaryText(data));
    },
    [api]
  );

  const loadAvailableModels = useCallback(async () => {
    try {
      const models = await api.listModels();
      setAvailableModels(models);
      setModelLoadError(null);
    } catch (error) {
      setAvailableModels([]);
      setModelLoadError((error as Error).message);
    }
  }, [api]);

  const createThread = useCallback(
    async (payload: { system_prompt: string; title: string | null }) => {
      const thread = await api.createThread(payload);
      setThreads((prev) => [thread, ...prev]);
      setActiveThreadId(thread.id);
    },
    [api]
  );

  const sendMessage = useCallback(async () => {
    if (!input.trim() || activeThreadId == null) return;
    setLoading(true);
    try {
      const result = await transport.sendMessage({
        threadId: activeThreadId,
        content: input.trim(),
        sender: "user",
        model: model || null,
      });
      setInput("");
      setMessages((prev) => [...prev, result.user_message, result.assistant_message]);
      await loadSummaries(activeThreadId);
    } finally {
      setLoading(false);
    }
  }, [activeThreadId, input, loadSummaries, model, transport]);

  useEffect(() => {
    void Promise.all([loadThreads(), loadAvailableModels()]);
  }, [loadAvailableModels, loadThreads]);

  useEffect(() => {
    if (activeThreadId != null) {
      void Promise.all([loadMessages(activeThreadId), loadSummaries(activeThreadId)]);
    }
  }, [activeThreadId, loadMessages, loadSummaries]);

  return {
    threads,
    activeThreadId,
    setActiveThreadId,
    messages,
    latestSummary,
    summaries,
    input,
    setInput,
    model,
    setModel,
    availableModels,
    modelLoadError,
    loading,
    createThread,
    sendMessage,
  };
}
