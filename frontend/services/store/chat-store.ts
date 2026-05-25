import { create } from "zustand";
import { persist } from "zustand/middleware";

export type MessageRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  metadata?: Record<string, unknown>;
  tokens_used?: number;
  created_at: string;
  // UI-only
  isStreaming?: boolean;
  isOptimistic?: boolean;
}

interface ChatState {
  // messages keyed by session_id
  messagesBySession: Record<string, ChatMessage[]>;
  streamingContent: string;
  isStreaming: boolean;
  isSending: boolean;
  error: string | null;

  setMessages: (sessionId: string, messages: ChatMessage[]) => void;
  addMessage: (sessionId: string, message: ChatMessage) => void;
  updateLastMessage: (sessionId: string, content: string, done?: boolean) => void;
  removeOptimistic: (sessionId: string) => void;
  setStreamingContent: (content: string) => void;
  appendStreamingContent: (token: string) => void;
  setIsStreaming: (v: boolean) => void;
  setIsSending: (v: boolean) => void;
  setError: (e: string | null) => void;
  getMessages: (sessionId: string) => ChatMessage[];
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
  messagesBySession: {},
  streamingContent: "",
  isStreaming: false,
  isSending: false,
  error: null,

  setMessages: (sessionId, messages) =>
    set((s) => ({
      messagesBySession: { ...s.messagesBySession, [sessionId]: messages },
    })),

  addMessage: (sessionId, message) =>
    set((s) => {
      const existing = s.messagesBySession[sessionId] ?? [];
      return {
        messagesBySession: {
          ...s.messagesBySession,
          [sessionId]: [...existing, message],
        },
      };
    }),

  updateLastMessage: (sessionId, content, done = false) =>
    set((s) => {
      const msgs = [...(s.messagesBySession[sessionId] ?? [])];
      if (!msgs.length) return {};
      const last = { ...msgs[msgs.length - 1], content, isStreaming: !done };
      msgs[msgs.length - 1] = last;
      return {
        messagesBySession: { ...s.messagesBySession, [sessionId]: msgs },
        ...(done ? { streamingContent: "", isStreaming: false } : {}),
      };
    }),

  removeOptimistic: (sessionId) =>
    set((s) => ({
      messagesBySession: {
        ...s.messagesBySession,
        [sessionId]: (s.messagesBySession[sessionId] ?? []).filter(
          (m) => !m.isOptimistic
        ),
      },
    })),

  setStreamingContent: (content) => set({ streamingContent: content }),
  appendStreamingContent: (token) =>
    set((s) => ({ streamingContent: s.streamingContent + token })),
  setIsStreaming: (v) => set({ isStreaming: v }),
  setIsSending: (v) => set({ isSending: v }),
  setError: (e) => set({ error: e }),
  getMessages: (sessionId) => get().messagesBySession[sessionId] ?? [],
    }),
    {
      name: "chat-store",
      partialize: (s) => ({ messagesBySession: s.messagesBySession }),
    }
  )
);
