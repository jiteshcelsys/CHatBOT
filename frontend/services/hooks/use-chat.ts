"use client";

import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect } from "react";
import { toast } from "sonner";
import { v4 as uuidv4 } from "uuid";
import { chatApi } from "@/services/api/chat-api";
import { useChatStore } from "@/services/store/chat-store";
import { useAuthStore } from "@/services/store/auth-store";

export function useChatHistory(sessionId: string | null) {
  const { setMessages } = useChatStore();

  const query = useQuery({
    queryKey: ["messages", sessionId],
    queryFn: () => chatApi.getHistory(sessionId!),
    enabled: !!sessionId,
    staleTime: 10_000,
  });

  useEffect(() => {
    if (query.data && sessionId) setMessages(sessionId, query.data);
  }, [query.data, sessionId, setMessages]);

  return query;
}

export function useChat(sessionId: string | null) {
  const { user } = useAuthStore();
  const {
    addMessage,
    updateLastMessage,
    removeOptimistic,
    setIsSending,
    setError,
    getMessages,
  } = useChatStore();

  const sendMessage = useCallback(
    async (content: string) => {
      if (!sessionId || !user?.uid || !content.trim()) return;

      setIsSending(true);
      setError(null);

      // Optimistic user message
      const optimisticUser = {
        id: `opt-${uuidv4()}`,
        session_id: sessionId,
        role: "user" as const,
        content,
        created_at: new Date().toISOString(),
        isOptimistic: true,
      };
      addMessage(sessionId, optimisticUser);

      // Optimistic AI placeholder
      const optimisticAI = {
        id: `opt-ai-${uuidv4()}`,
        session_id: sessionId,
        role: "assistant" as const,
        content: "…",
        created_at: new Date().toISOString(),
        isOptimistic: true,
        isStreaming: false,
      };
      addMessage(sessionId, optimisticAI);

      try {
        const result = await chatApi.send({
          message: content,
          session_id: sessionId,
          user_id: user.uid,
          collection: process.env.NEXT_PUBLIC_DEFAULT_COLLECTION ?? "documents",
        });

        // Replace optimistic messages with real ones
        removeOptimistic(sessionId);
        addMessage(sessionId, {
          id: uuidv4(),
          session_id: sessionId,
          role: "user",
          content,
          created_at: new Date().toISOString(),
        });
        addMessage(sessionId, {
          id: uuidv4(),
          session_id: sessionId,
          role: "assistant",
          content: result.response,
          metadata: {
            model: result.model,
            tokens: result.tokens,
            retrieval_used: result.retrieval_used,
          },
          tokens_used: result.tokens.total,
          created_at: result.timestamp,
        });
      } catch (err) {
        removeOptimistic(sessionId);
        const msg = err instanceof Error ? err.message : "Failed to send";
        setError(msg);
        toast.error(msg);
      } finally {
        setIsSending(false);
      }
    },
    [sessionId, user, addMessage, removeOptimistic, setIsSending, setError]
  );

  const isSending = useChatStore((s) => s.isSending);
  const error = useChatStore((s) => s.error);

  return {
    messages: getMessages(sessionId ?? ""),
    sendMessage,
    isSending,
    error,
  };
}
