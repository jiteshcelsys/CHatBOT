"use client";
import { useSessionStore } from "@/services/store/session-store";
import { ConversationItem } from "./conversation-item";

export function ConversationList({ onClose }: { onClose?: () => void }) {
  const { sessions, activeSessionId, setActiveSession } = useSessionStore();

  if (sessions.length === 0) {
    return (
      <p className="px-3 py-4 text-xs text-muted-foreground text-center select-none">
        No conversations yet
      </p>
    );
  }

  const sorted = [...sessions].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  );

  return (
    <div className="flex flex-col gap-0.5 px-2">
      {sorted.map((s) => (
        <ConversationItem
          key={s.id}
          session={s}
          isActive={s.id === activeSessionId}
          onSelect={() => { setActiveSession(s.id); onClose?.(); }}
        />
      ))}
    </div>
  );
}
