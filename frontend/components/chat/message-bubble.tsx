"use client";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { StreamingMessage } from "./streaming-message";
import type { ChatMessage } from "@/services/store/chat-store";

interface Props {
  message: ChatMessage;
  userPhotoURL?: string;
  userDisplayName?: string;
}

export function MessageBubble({ message, userPhotoURL, userDisplayName }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex items-start gap-3 group", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <Avatar className="h-8 w-8 shrink-0 mt-0.5">
        {isUser ? (
          <>
            <AvatarImage src={userPhotoURL} />
            <AvatarFallback className="bg-primary text-primary-foreground text-xs">
              {(userDisplayName?.[0] ?? "U").toUpperCase()}
            </AvatarFallback>
          </>
        ) : (
          <AvatarFallback className="bg-violet-600 text-white text-xs">AI</AvatarFallback>
        )}
      </Avatar>

      {/* Bubble */}
      <div
        className={cn(
          "max-w-[78%] rounded-2xl px-4 py-2.5 text-sm shadow-sm",
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-sm"
            : "bg-muted text-foreground rounded-tl-sm"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <StreamingMessage
            content={message.content}
            isStreaming={message.isStreaming}
          />
        )}

        <p
          className={cn(
            "mt-1 text-[10px] select-none",
            isUser ? "text-primary-foreground/60 text-right" : "text-muted-foreground"
          )}
        >
          {new Date(message.created_at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
          {message.tokens_used ? ` · ${message.tokens_used} tokens` : ""}
        </p>
      </div>
    </div>
  );
}
