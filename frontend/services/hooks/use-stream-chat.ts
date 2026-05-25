"use client";

import { useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { toast } from "sonner";
import { chatApi } from "@/services/api/chat-api";
import { useChatStore } from "@/services/store/chat-store";
import { useAuthStore } from "@/services/store/auth-store";

export function useStreamChat(sessionId: string | null) {
  const { user } = useAuthStore();
  const {
    addMessage,
    updateLastMessage,
    removeOptimistic,
    setIsStreaming,
    appendStreamingContent,
    setStreamingContent,
    setIsSending,
    setError,
    getMessages,
  } = useChatStore();

  const abortRef = useRef<(() => void) | null>(null);

  const sendStream = useCallback(
    (content: string) => {
      if (!sessionId || !content.trim()) return;
    const userId = user?.uid ?? "local";

      setIsSending(true);
      setIsStreaming(true);
      setStreamingContent("");
      setError(null);

      // Optimistic user bubble
      const userMsgId = uuidv4();
      addMessage(sessionId, {
        id: userMsgId,
        session_id: sessionId,
        role: "user",
        content,
        created_at: new Date().toISOString(),
        isOptimistic: true,
      });

      // Empty AI bubble that will be filled by stream
      const aiMsgId = uuidv4();
      addMessage(sessionId, {
        id: aiMsgId,
        session_id: sessionId,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
        isOptimistic: true,
        isStreaming: true,
      });

      let accumulated = "";

      const cancel = chatApi.stream(
        {
          message: content,
          session_id: sessionId,
          user_id: userId,
          collection: process.env.NEXT_PUBLIC_DEFAULT_COLLECTION ?? "documents",
        },
        (token) => {
          accumulated += token;
          updateLastMessage(sessionId, accumulated, false);
          appendStreamingContent(token);
        },
        (_meta) => {
          updateLastMessage(sessionId, accumulated, true);
          // Mark last message as non-optimistic and non-streaming
          const msgs = getMessages(sessionId);
          const last = msgs[msgs.length - 1];
          if (last) {
            Object.assign(last, { isOptimistic: false, isStreaming: false });
          }
          setIsStreaming(false);
          setIsSending(false);
        },
        (err) => {
          removeOptimistic(sessionId);
          setIsStreaming(false);
          setIsSending(false);
          setError(err.message);
          toast.error(err.message);
        }
      );

      abortRef.current = cancel;
    },
    [
      sessionId, user,
      addMessage, updateLastMessage, removeOptimistic,
      appendStreamingContent, setStreamingContent,
      setIsStreaming, setIsSending, setError, getMessages,
    ]
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.();
    setIsStreaming(false);
    setIsSending(false);
  }, [setIsStreaming, setIsSending]);

  const isStreaming = useChatStore((s) => s.isStreaming);
  const isSending = useChatStore((s) => s.isSending);
  const streamingContent = useChatStore((s) => s.streamingContent);

  return {
    messages: getMessages(sessionId ?? ""),
    sendStream,
    cancelStream,
    isStreaming,
    isSending,
    streamingContent,
  };
}
