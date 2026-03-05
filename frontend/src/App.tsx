import React, { useMemo } from "react";

import { HttpChatApi } from "./api/httpChatApi";
import { useChatStore } from "./state/chatStore";

const App: React.FC = () => {
  const api = useMemo(() => new HttpChatApi(), []);
  const {
    threads,
    activeThreadId,
    setActiveThreadId,
    messages,
    latestSummary,
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
    const systemPrompt = window.prompt(
      "System prompt for this thread:",
      "You are a helpful assistant."
    );
    if (!systemPrompt) return;
    const title = window.prompt("Optional title:", "") || null;
    await createThread({ system_prompt: systemPrompt, title });
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

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>superq-chat</h1>
          <button onClick={handleCreateThread}>New thread</button>
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
                {t.title || `Thread #${t.id}`}
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
              Multi-agent chat with hierarchical summaries.
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
          <h3>Summary</h3>
          <p>{latestSummary || "No summary yet."}</p>
        </section>
        <section className="messages-panel">
          <div className="messages">
            {messages.map((m) => (
              <div key={m.id} className={`msg msg-${m.role}`}>
                <span className="msg-role">{m.role.toUpperCase()}:</span>
                <span className="msg-content">{m.content}</span>
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

