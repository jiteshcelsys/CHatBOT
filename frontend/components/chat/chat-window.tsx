"use client";
import { MessageList } from "./message-list";
import { MessageInput } from "./message-input";
import { useStreamChat } from "@/services/hooks/use-stream-chat";
import { useChatStore } from "@/services/store/chat-store";
import { useSessionStore } from "@/services/store/session-store";
import { useAuthStore } from "@/services/store/auth-store";

export function ChatWindow() {
  const { user } = useAuthStore();
  const { activeSessionId } = useSessionStore();
  const messagesBySession = useChatStore((s) => s.messagesBySession);
  const messages = activeSessionId ? (messagesBySession[activeSessionId] ?? []) : [];

  const { sendStream, cancelStream, isStreaming, isSending } = useStreamChat(activeSessionId ?? null);

  const handleSend = (content: string, _stream: boolean) => {
    sendStream(content);
  };

  if (!activeSessionId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground select-none">
        <div className="text-5xl">💬</div>
        <p className="text-lg font-medium text-foreground">No conversation selected</p>
        <p className="text-sm">Pick one from the sidebar or start a new chat.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <MessageList
        messages={messages}
        userPhotoURL={user?.photoURL ?? undefined}
        userDisplayName={user?.displayName ?? undefined}
        isLoading={isSending && !isStreaming}
      />
      <MessageInput
        onSend={handleSend}
        disabled={isSending}
        streaming={isStreaming}
        onAbort={cancelStream}
      />
    </div>
  );
}
