import apiClient from "./client";
import type { ChatSession } from "@/services/store/session-store";

interface CreateSessionPayload {
  title?: string;
  collection?: string;
}

export const sessionApi = {
  create: async (payload: CreateSessionPayload = {}): Promise<ChatSession> => {
    const { data } = await apiClient.post("/chat/session/create", payload);
    return data.data as ChatSession;
  },

  list: async (activeOnly = true): Promise<ChatSession[]> => {
    const { data } = await apiClient.get("/chat/sessions", {
      params: { active_only: activeOnly },
    });
    return (data.data ?? []) as ChatSession[];
  },

  rename: async (sessionId: string, title: string): Promise<void> => {
    await apiClient.patch(`/chat/session/${sessionId}`, { title });
  },

  delete: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/chat/session/${sessionId}`);
  },
};
