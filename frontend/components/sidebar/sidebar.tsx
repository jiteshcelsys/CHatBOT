"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ConversationList } from "./conversation-list";
import { FileUpload } from "./file-upload";
import { useAuthStore } from "@/services/store/auth-store";
import { useSessionStore } from "@/services/store/session-store";
import { sessionApi } from "@/services/api/session-api";
import { logout } from "@/lib/firebase/auth";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface Props {
  className?: string;
}

export function Sidebar({ className }: Props) {
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();
  const { addSession, setActiveSession } = useSessionStore();
  const [creating, setCreating] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);

  const handleNewChat = async () => {
    setCreating(true);
    try {
      const session = await sessionApi.create({ title: "New Chat" });
      addSession(session);
      setActiveSession(session.id);
    } catch {
      const localSession = {
        id: crypto.randomUUID(),
        user_id: user?.uid ?? "local",
        title: "New Chat",
        collection: "documents",
        is_active: true,
        message_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      addSession(localSession);
      setActiveSession(localSession.id);
    } finally {
      setCreating(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    clearAuth();
    router.replace("/login");
  };

  return (
    <aside className={cn("flex flex-col h-full bg-sidebar border-r", className)}>
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b">
        <div className="h-7 w-7 rounded-full bg-violet-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
          AI
        </div>
        <span className="font-semibold text-sm truncate">AI Chatbot</span>
      </div>

      {/* New Chat */}
      <div className="px-3 pt-3 pb-1">
        <Button
          className="w-full justify-start gap-2 rounded-lg text-sm"
          variant="outline"
          size="sm"
          onClick={handleNewChat}
          disabled={creating}
        >
          <span>+</span>
          {creating ? "Creating…" : "New chat"}
        </Button>
      </div>

      {/* Upload Documents toggle */}
      <div className="px-3 pb-2">
        <button
          onClick={() => setUploadOpen((v) => !v)}
          className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <span>📄</span>
            Upload documents
          </span>
          <span className={cn("transition-transform", uploadOpen && "rotate-180")}>▾</span>
        </button>

        {uploadOpen && (
          <div className="mt-1 rounded-lg border bg-muted/30">
            <FileUpload />
          </div>
        )}
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        <p className="px-4 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 select-none">
          Conversations
        </p>
        <ConversationList />
      </div>

      {/* User footer */}
      <div className="border-t px-3 py-3">
        <div className="flex items-center gap-2">
          <Avatar className="h-7 w-7 shrink-0">
            <AvatarImage src={user?.photoURL ?? undefined} />
            <AvatarFallback className="bg-primary text-primary-foreground text-xs">
              {(user?.displayName?.[0] ?? user?.email?.[0] ?? "U").toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium truncate">{user?.displayName ?? user?.email ?? "User"}</p>
          </div>
          <button
            onClick={handleLogout}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0"
            title="Sign out"
          >
            ↩
          </button>
        </div>
      </div>
    </aside>
  );
}
