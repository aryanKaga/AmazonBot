"use client";
import { useState, useRef, useEffect } from "react";
import { signOut } from "next-auth/react";
import styles from "./ChatPage.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

interface Message {
  role: "user" | "assistant" | "system";
  text: string;
  confidence?: number;
  status?: "completed" | "escalated";
  ticket?: string;
}

interface User {
  name?: string | null;
  email?: string | null;
  id?: string;
}

export default function ChatPage({ user }: { user?: User }) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "system",
      text: `Hello ${user?.name ?? "there"}! 👋 I'm your Amazon support assistant. Ask me about your orders, returns, account, or anything else.`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const pollStatus = async (taskId: string): Promise<any> => {
    while (true) {
      await new Promise((r) => setTimeout(r, 1000));
      const res = await fetch(`${API_BASE}/chat/status/${taskId}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (data.status !== "pending") return data;
    }
  };

  const sendMessage = async () => {
    const query = input.trim();
    if (!query || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: query }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          session_id: sessionId,
          user_id: user?.id ?? "anonymous",
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const { task_id } = await res.json();
      const result = await pollStatus(task_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: result.answer ?? "I need to hand this off to a human agent.",
          confidence: result.confidence,
          status: result.status,
          ticket: result.human_bucket?.ticket?.ticket_id,
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `⚠️ Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearSession = async () => {
    await fetch(`${API_BASE}/sessions/${sessionId}`, { method: "DELETE" });
    setMessages([
      {
        role: "system",
        text: `New conversation started. How can I help you today?`,
      },
    ]);
  };

  return (
    <div className={styles.layout}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarLogo}>
          <div className={styles.logoIcon}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="url(#g2)" />
              <path d="M2 17l10 5 10-5" stroke="url(#g2)" strokeWidth="2" strokeLinecap="round" />
              <path d="M2 12l10 5 10-5" stroke="url(#g2)" strokeWidth="2" strokeLinecap="round" />
              <defs>
                <linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#6382ff" />
                  <stop offset="100%" stopColor="#a78bfa" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span className={styles.sidebarTitle}>AmazonBot</span>
        </div>

        <nav className={styles.sidebarNav}>
          <button id="new-chat-btn" className={`${styles.navItem} ${styles.navActive}`}>
            <ChatIcon /> Chat
          </button>
          <button
            id="new-conversation-btn"
            className={styles.navItem}
            onClick={clearSession}
          >
            <PlusIcon /> New Chat
          </button>
          <a
            id="tickets-link"
            href={`${API_BASE}/human-bucket`}
            target="_blank"
            className={styles.navItem}
          >
            <TicketIcon /> Human Tickets
          </a>
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userChip}>
            <div className={styles.avatar}>{user?.name?.[0] ?? "U"}</div>
            <div>
              <div className={styles.userName}>{user?.name}</div>
              <div className={styles.userEmail}>{user?.email}</div>
            </div>
          </div>
          <button
            id="signout-btn"
            className="btn btn-ghost"
            onClick={() => signOut({ callbackUrl: "/login" })}
            style={{ width: "100%", marginTop: 8, justifyContent: "center", fontSize: "0.8rem" }}
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className={styles.main}>
        <header className={styles.header}>
          <h1 className={styles.headerTitle}>Amazon Support</h1>
          <span className={styles.badge}>AI + RAG</span>
        </header>

        <div className={styles.messages}>
          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        <div className={styles.inputRow}>
          <textarea
            id="chat-input"
            className={`input ${styles.textarea}`}
            placeholder="Ask about your order, return, account…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={loading}
          />
          <button
            id="send-btn"
            className={`btn btn-primary ${styles.sendBtn}`}
            onClick={sendMessage}
            disabled={loading || !input.trim()}
          >
            {loading ? <Spinner /> : <SendIcon />}
          </button>
        </div>
      </main>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const isEscalated = message.status === "escalated";

  return (
    <div
      className={`${styles.bubble} ${
        isUser ? styles.bubbleUser : isSystem ? styles.bubbleSystem : styles.bubbleBot
      }`}
      style={{ animationDelay: `${Math.random() * 0.1}s` }}
    >
      {!isUser && !isSystem && (
        <div className={styles.botAvatar}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="url(#ga)" />
            <path d="M9 12l2 2 4-4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <defs>
              <linearGradient id="ga" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#6382ff" />
                <stop offset="100%" stopColor="#a78bfa" />
              </linearGradient>
            </defs>
          </svg>
        </div>
      )}
      <div className={styles.bubbleContent}>
        <p className={styles.bubbleText}>{message.text}</p>
        {isEscalated && (
          <div className={styles.escalatedBadge}>
            🎫 Escalated to human agent
            {message.ticket && <span> · Ticket: <code>{message.ticket}</code></span>}
          </div>
        )}
        {message.confidence != null && !isEscalated && (
          <div className={styles.confidenceBar}>
            <div
              className={styles.confidenceFill}
              style={{
                width: `${Math.round(message.confidence * 100)}%`,
                background:
                  message.confidence > 0.7
                    ? "var(--color-success)"
                    : message.confidence > 0.45
                    ? "var(--color-warning)"
                    : "var(--color-danger)",
              }}
            />
            <span className={styles.confidenceLabel}>
              {Math.round(message.confidence * 100)}% confidence
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className={`${styles.bubble} ${styles.bubbleBot}`}>
      <div className={styles.botAvatar}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" fill="url(#gt)" />
          <defs>
            <linearGradient id="gt" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#6382ff" />
              <stop offset="100%" stopColor="#a78bfa" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      <div className={styles.typingDots}>
        <span style={{ animationDelay: "0s" }} />
        <span style={{ animationDelay: "0.2s" }} />
        <span style={{ animationDelay: "0.4s" }} />
      </div>
    </div>
  );
}

const ChatIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);
const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);
const TicketIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
  </svg>
);
const SendIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);
const Spinner = () => <span className={styles.spinner} />;
