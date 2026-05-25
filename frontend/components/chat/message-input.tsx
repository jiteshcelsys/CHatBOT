"use client";
import { useRef, useState, KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface Props {
  onSend: (content: string, stream: boolean) => void;
  disabled?: boolean;
  streaming?: boolean;
  onAbort?: () => void;
}

export function MessageInput({ onSend, disabled, streaming, onAbort }: Props) {
  const [value, setValue] = useState("");
  const [streamMode, setStreamMode] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed, streamMode);
    setValue("");
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t bg-background px-4 py-3">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-2xl border bg-background shadow-sm px-3 py-2 focus-within:ring-2 focus-within:ring-ring">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message… (Shift+Enter for newline)"
            disabled={disabled || streaming}
            rows={1}
            className="flex-1 resize-none border-0 shadow-none focus-visible:ring-0 min-h-[36px] max-h-[200px] py-1 px-0 text-sm"
          />

          <div className="flex items-center gap-1.5 pb-0.5 shrink-0">
            <button
              type="button"
              onClick={() => setStreamMode((s) => !s)}
              className={cn(
                "text-[10px] font-medium px-2 py-1 rounded-full border transition-colors select-none",
                streamMode
                  ? "border-violet-500 text-violet-600 bg-violet-50 dark:bg-violet-950/30"
                  : "border-muted-foreground/30 text-muted-foreground"
              )}
              title="Toggle streaming mode"
            >
              {streamMode ? "Stream" : "Full"}
            </button>

            {streaming ? (
              <Button
                size="sm"
                variant="destructive"
                className="h-8 px-3 rounded-xl text-xs"
                onClick={onAbort}
              >
                Stop
              </Button>
            ) : (
              <Button
                size="sm"
                className="h-8 px-3 rounded-xl text-xs"
                onClick={handleSend}
                disabled={!value.trim() || disabled}
              >
                Send
              </Button>
            )}
          </div>
        </div>
        <p className="text-center text-[10px] text-muted-foreground/50 mt-1.5 select-none">
          AI can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  );
}
