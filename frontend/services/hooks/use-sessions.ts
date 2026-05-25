"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";
import { sessionApi } from "@/services/api/session-api";
import { useSessionStore } from "@/services/store/session-store";
import { useAuthStore } from "@/services/store/auth-store";

export function useSessions() {
  const { user } = useAuthStore();
  const { setSessions, addSession, removeSession, setActiveSession, activeSessionId } =
    useSessionStore();
  const qc = useQueryClient();

  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ["sessions", user?.uid],
    queryFn: () => sessionApi.list(),
    enabled: !!user?.uid,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (sessions.length > 0) setSessions(sessions);
  }, [sessions, setSessions]);

  const createMutation = useMutation({
    mutationFn: (title?: string) =>
      sessionApi.create({
        title: title ?? "New Chat",
        collection: process.env.NEXT_PUBLIC_DEFAULT_COLLECTION ?? "documents",
      }),
    onSuccess: (session) => {
      addSession(session);
      qc.invalidateQueries({ queryKey: ["sessions"] });
      toast.success("New conversation created");
    },
    onError: () => toast.error("Failed to create session"),
  });

  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => sessionApi.delete(sessionId),
    onSuccess: (_data, sessionId) => {
      removeSession(sessionId);
      qc.invalidateQueries({ queryKey: ["sessions"] });
      toast.success("Conversation deleted");
    },
    onError: () => toast.error("Failed to delete session"),
  });

  return {
    sessions,
    isLoading,
    activeSessionId,
    setActiveSession,
    createSession: createMutation.mutate,
    isCreating: createMutation.isPending,
    deleteSession: deleteMutation.mutate,
    isDeleting: deleteMutation.isPending,
  };
}
