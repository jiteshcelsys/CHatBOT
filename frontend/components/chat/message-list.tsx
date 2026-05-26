"use client";
import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import { TypingIndicator } from "./typing-indicator";
import type { ChatMessage } from "@/services/store/chat-store";

interface Props {
  messages: ChatMessage[];
  userPhotoURL?: string;
  userDisplayName?: string;
  isLoading?: boolean;
}

export function MessageList({ messages, userPhotoURL, userDisplayName, isLoading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground text-sm select-none">
        Start a conversation…
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1 px-2 sm:px-4 py-4">
      <div className="mx-auto max-w-3xl flex flex-col gap-4">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            userPhotoURL={userPhotoURL}
            userDisplayName={userDisplayName}
          />
        ))}
        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-full bg-violet-600 flex items-center justify-center text-white text-xs shrink-0 mt-0.5">
              AI
            </div>
            <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-2.5">
              <TypingIndicator />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
