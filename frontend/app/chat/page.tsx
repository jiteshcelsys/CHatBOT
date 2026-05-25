"use client";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar/sidebar";
import { ChatWindow } from "@/components/chat/chat-window";
import { useAuthStore } from "@/services/store/auth-store";
import { useSessionStore } from "@/services/store/session-store";
import { sessionApi } from "@/services/api/session-api";

export default function ChatPage() {
  const { user } = useAuthStore();
  const { sessions, setSessions, activeSessionId } = useSessionStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [bootstrapped, setBootstrapped] = useState(false);

  useEffect(() => {
    if (!user || bootstrapped) return;
    setBootstrapped(true);
    sessionApi.list().then((list) => {
      if (list.length > 0) setSessions(list);
    }).catch(() => {});
  }, [user, bootstrapped, setSessions]);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar toggle for mobile */}
      <button
        className="fixed top-3 left-3 z-50 md:hidden p-1.5 rounded-lg bg-background border shadow-sm"
        onClick={() => setSidebarOpen((v) => !v)}
        aria-label="Toggle sidebar"
      >
        ☰
      </button>

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-200
        md:relative md:translate-x-0 md:flex md:flex-col
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
      `}>
        <Sidebar className="h-full" />
      </div>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <ChatWindow />
      </main>
    </div>
  );
}
