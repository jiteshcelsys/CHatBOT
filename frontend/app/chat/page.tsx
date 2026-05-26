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
  const [sidebarOpen, setSidebarOpen] = useState(false);
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
        className="fixed top-3 left-3 z-50 md:hidden p-2 rounded-lg bg-background border shadow-sm"
        onClick={() => setSidebarOpen((v) => !v)}
        aria-label="Toggle sidebar"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <line x1="2" y1="4.5" x2="16" y2="4.5" />
          <line x1="2" y1="9" x2="16" y2="9" />
          <line x1="2" y1="13.5" x2="16" y2="13.5" />
        </svg>
      </button>

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-40 w-72 transform transition-transform duration-300
        md:relative md:z-auto md:w-64 md:translate-x-0 md:flex md:flex-col
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
      `}>
        <Sidebar
          className="h-full"
          mobileOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
      </div>

      {/* Overlay for mobile — fully opaque so content is completely hidden */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/80 md:hidden backdrop-blur-sm"
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
