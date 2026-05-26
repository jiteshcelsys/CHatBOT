"use client";
import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useSessionStore, type ChatSession } from "@/services/store/session-store";
import { sessionApi } from "@/services/api/session-api";

interface Props {
  session: ChatSession;
  isActive: boolean;
  onSelect: () => void;
}

export function ConversationItem({ session, isActive, onSelect }: Props) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(session.title);
  const [menuOpen, setMenuOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { renameSession, removeSession } = useSessionStore();

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  const handleRename = async () => {
    const trimmed = title.trim();
    if (!trimmed) { setTitle(session.title); setEditing(false); return; }
    renameSession(session.id, trimmed);
    setEditing(false);
    try { await sessionApi.rename(session.id, trimmed); } catch {}
  };

  const handleDelete = async () => {
    setMenuOpen(false);
    removeSession(session.id);
    try { await sessionApi.delete(session.id); } catch {}
  };

  return (
    <div
      className={cn(
        "group relative flex items-center gap-2 rounded-lg px-2.5 py-2 cursor-pointer text-sm transition-colors",
        isActive ? "bg-accent text-accent-foreground" : "hover:bg-accent/50 text-muted-foreground hover:text-foreground"
      )}
      onClick={() => { if (!editing) onSelect(); }}
    >
      <span className="text-base shrink-0 select-none">💬</span>

      {editing ? (
        <input
          ref={inputRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={handleRename}
          onKeyDown={(e) => { if (e.key === "Enter") handleRename(); if (e.key === "Escape") { setTitle(session.title); setEditing(false); } }}
          onClick={(e) => e.stopPropagation()}
          className="flex-1 bg-transparent outline-none text-sm text-foreground"
        />
      ) : (
        <span className="flex-1 truncate">{session.title}</span>
      )}

      {!editing && (
        <div className={cn("flex gap-0.5 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity", isActive && "sm:opacity-100")}>
          <button
            className="p-0.5 rounded hover:bg-background/50 text-xs"
            onClick={(e) => { e.stopPropagation(); setEditing(true); }}
            title="Rename"
          >
            ✏️
          </button>
          <button
            className="p-0.5 rounded hover:bg-destructive/20 text-xs"
            onClick={(e) => { e.stopPropagation(); handleDelete(); }}
            title="Delete"
          >
            🗑️
          </button>
        </div>
      )}
    </div>
  );
}
