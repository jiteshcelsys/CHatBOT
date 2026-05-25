import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ChatSession {
  id: string;
  user_id: string;
  title: string;
  collection: string;
  is_active: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

interface SessionState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  setSessions: (sessions: ChatSession[]) => void;
  addSession: (session: ChatSession) => void;
  updateSession: (id: string, updates: Partial<ChatSession>) => void;
  removeSession: (id: string) => void;
  renameSession: (id: string, title: string) => void;
  setActiveSession: (id: string | null) => void;
  getActiveSession: () => ChatSession | null;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeSessionId: null,

      setSessions: (sessions) => set({ sessions }),

      addSession: (session) =>
        set((s) => ({
          sessions: [session, ...s.sessions],
          activeSessionId: session.id,
        })),

      updateSession: (id, updates) =>
        set((s) => ({
          sessions: s.sessions.map((sess) =>
            sess.id === id ? { ...sess, ...updates } : sess
          ),
        })),

      removeSession: (id) =>
        set((s) => ({
          sessions: s.sessions.filter((sess) => sess.id !== id),
          activeSessionId: s.activeSessionId === id ? null : s.activeSessionId,
        })),

      renameSession: (id, title) =>
        set((s) => ({
          sessions: s.sessions.map((sess) =>
            sess.id === id ? { ...sess, title } : sess
          ),
        })),

      setActiveSession: (id) => set({ activeSessionId: id }),

      getActiveSession: () => {
        const { sessions, activeSessionId } = get();
        return sessions.find((s) => s.id === activeSessionId) ?? null;
      },
    }),
    {
      name: "session-store",
    }
  )
);
