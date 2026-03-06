import React, { useMemo } from "react";
import ReactMarkdown from "react-markdown";

import { HttpChatApi } from "./api/httpChatApi";
import { useChatStore } from "./state/chatStore";
import type { Summary } from "./models/summaryViewModel";

const App: React.FC = () => {
  const api = useMemo(() => new HttpChatApi(), []);
  const {
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
    loading,
    createThread,
    sendMessage,
  } = useChatStore(api);

  async function handleCreateThread() {
    await createThread({
      system_prompt: "You are a helpful assistant.",
      title: null,
    });
  }

  async function handleSend() {
    try {
      await sendMessage();
    } catch (e) {
      console.error(e);
      window.alert((e as Error).message);
    }
  }

  const activeThread = threads.find((t) => t.id === activeThreadId) ?? null;
  const getRoleLabel = (role: string) => {
    if (role === "user") return "You";
    if (role === "assistant") return "Assistant";
    return role;
  };

  const getSummaryLabel = (s: Summary) =>
    s.level === 2 ? "Global Summary" : "Local Summary";

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>ChatGenie</h1>
          <button onClick={handleCreateThread}>New Chat</button>
        </div>
        <div className="thread-list">
          {threads.map((t) => (
            <button
              key={t.id}
              className={
                "thread-item" + (t.id === activeThreadId ? " active" : "")
              }
              onClick={() => setActiveThreadId(t.id)}
            >
              <span className="thread-title">
                {t.title || `Chat #${t.id}`}
              </span>
            </button>
          ))}
          {!threads.length && <p className="empty">No threads yet.</p>}
        </div>
      </aside>
      <main className="main">
        <header className="main-header">
          <div>
            <h2>{activeThread?.title || "Conversation"}</h2>
            <p className="subtitle">
              Memory-aware chat system with threaded conversations, model switching, and automatic summarization.
            </p>
          </div>
          <div className="model-select">
            <label>
              Model
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
              >
                <option value="">default</option>
                {availableModels.map((m) => (
                  <option key={m.key} value={m.key}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </header>
        <section className="summary-panel">
          <h3>Summaries</h3>
          {summaries.length > 0 ? (
            <div className="summary-list">
              {summaries.map((s) => (
                <div
                  key={s.id}
                  className={`summary-card summary-level-${s.level}`}
                >
                  <div className="summary-header">
                    <span className="summary-label">{getSummaryLabel(s)}</span>
                    <span className="summary-time">
                      {new Date(s.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="summary-content">
                    <ReactMarkdown>{s.summary_text}</ReactMarkdown>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty">No summaries yet.</p>
          )}
        </section>
        <section className="messages-panel">
          <div className="messages">
            {messages.map((m) => (
              <div key={m.id} className={`msg msg-${m.role}`}>
                <span className="msg-role">{getRoleLabel(m.role)}:</span>
                <div className="msg-content">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
              </div>
            ))}
            {!messages.length && (
              <p className="empty">No messages yet. Start the conversation!</p>
            )}
          </div>
        </section>
        <footer className="composer">
          <textarea
            placeholder="Type a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
          />
          <button onClick={handleSend} disabled={loading || !input.trim()}>
            {loading ? "Sending..." : "Send"}
          </button>
        </footer>
      </main>
    </div>
  );
};

export default App;

