import apiClient from "./client";
import type { ChatMessage } from "@/services/store/chat-store";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SendMessagePayload {
  message: string;
  session_id: string;
  user_id: string;
  collection?: string;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  model: string;
  finish_reason: string;
  retrieval_used: boolean;
  chunks_retrieved: number;
  tokens: { prompt: number; completion: number; total: number };
  timestamp: string;
  error: string | null;
}

export const chatApi = {
  /** Full (non-streaming) response */
  send: async (payload: SendMessagePayload): Promise<ChatResponse> => {
    const { data } = await apiClient.post("/chat/", payload);
    return data.data as ChatResponse;
  },

  /** Returns an SSE EventSource (caller must close it) */
  stream: (
    payload: SendMessagePayload,
    onToken: (token: string) => void,
    onDone: (meta: { session_id: string; total_chars: number }) => void,
    onError: (err: Error) => void
  ): (() => void) => {
    // SSE via fetch + ReadableStream (EventSource doesn't support POST)
    const controller = new AbortController();

    (async () => {
      try {
        // We need the auth token — read from store directly
        const { useAuthStore } = await import("@/services/store/auth-store");
        const token = useAuthStore.getState().user?.token ?? "";

        const response = await fetch(`${BASE_URL}/api/v1/chat/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Stream error: ${response.status}`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (raw === "[DONE]") return;

            try {
              const event = JSON.parse(raw);
              if (event.type === "token") onToken(event.content);
              if (event.type === "done") onDone(event.metadata);
            } catch {
              // malformed line — skip
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          onError(err as Error);
        }
      }
    })();

    return () => controller.abort();
  },

  getHistory: async (
    sessionId: string,
    limit = 50,
    offset = 0
  ): Promise<ChatMessage[]> => {
    const { data } = await apiClient.get(`/chat/history/${sessionId}`, {
      params: { limit, offset },
    });
    return (data.data ?? []) as ChatMessage[];
  },
};
