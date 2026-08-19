
"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Logo from "@/app/Logo.png";
import { ChatMessage, type Message } from "@/components/chat/chat-message";
import { ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SampleQuestions } from "@/app/components/chat/sample-questions";

type ChatWindowProps = {
  messages: Message[];
  isStreaming: boolean;
  onQuestionClick: (question: string) => void;
  onRetry?: (messageIndex: number) => void;
};

// How close to the bottom (px) still counts as "at the bottom"
const BOTTOM_THRESHOLD = 96;

export function ChatWindow({ messages, isStreaming, onQuestionClick, onRetry }: ChatWindowProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const atBottomRef = useRef(true);
  const prevCountRef = useRef(0);
  const streamingByIdRef = useRef<Map<string, boolean>>(new Map());
  const [showJump, setShowJump] = useState(false);

  // Auto-follow rules: a new message always scrolls into view; streamed
  // content only keeps the view pinned while the reader is already at the
  // bottom; and when an answer finishes, the view jumps back to the TOP of
  // that answer so it can be read from the beginning.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Detect an assistant message transitioning streaming -> done
    let completedId: string | null = null;
    for (const m of messages) {
      if (m.role === "assistant" && m.id) {
        if (streamingByIdRef.current.get(m.id) && !m.streaming) completedId = m.id;
        streamingByIdRef.current.set(m.id, !!m.streaming);
      }
    }

    const isNewMessage = messages.length !== prevCountRef.current;
    prevCountRef.current = messages.length;

    if (completedId) {
      const el = container.querySelector<HTMLElement>(`[data-msg-id="${CSS.escape(completedId)}"]`);
      if (el) {
        const top = el.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop;
        container.scrollTop = Math.max(0, top - 8);
        atBottomRef.current = false;
        return; // don't pin to bottom on the completion update
      }
    }

    if (isNewMessage || atBottomRef.current) {
      container.scrollTop = container.scrollHeight;
      atBottomRef.current = true;
      setShowJump(false);
    }
  }, [messages]);

  const handleScroll = () => {
    const container = containerRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    const atBottom = distanceFromBottom < BOTTOM_THRESHOLD;
    atBottomRef.current = atBottom;
    setShowJump((prev) => (prev === !atBottom ? prev : !atBottom));
  };

  const jumpToBottom = () => {
    const container = containerRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  };

  const lastAssistantIndex = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return i;
    }
    return -1;
  })();

  return (
    <div className="relative h-full">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto overscroll-contain"
        aria-live="polite"
      >
        <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center pt-1 text-center sm:pt-4">
              <div className="flex items-center justify-center gap-2.5">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/15">
                  <Image src={Logo} alt="Dunia logo" width={26} height={26} className="h-[26px] w-[26px]" />
                </div>
                <h1 className="text-lg font-semibold tracking-tight text-foreground sm:text-xl">
                  Welcome to Dunia
                </h1>
              </div>
              <p className="mt-2.5 max-w-md text-[13px] leading-5 text-muted-foreground">
                Dunia means &ldquo;world&rdquo; in Swahili. Ask me about climate change in any
                language — every answer comes with verified sources.
              </p>
              <div className="mt-5 w-full">
                <p className="mb-2.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Try asking
                </p>
                <SampleQuestions onQuestionClick={onQuestionClick} />
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg, index) => (
                <div key={msg.id || index} data-msg-id={msg.id}>
                  <ChatMessage
                    message={msg}
                    onRetry={
                      msg.role === "assistant" && onRetry && index === lastAssistantIndex && !isStreaming
                        ? () => onRetry(index)
                        : undefined
                    }
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showJump && (
        <div className="pointer-events-none absolute inset-x-0 bottom-4 flex justify-center">
          <Button
            variant="outline"
            size="icon"
            onClick={jumpToBottom}
            className="pointer-events-auto h-9 w-9 rounded-full border bg-card shadow-md"
            aria-label="Jump to latest message"
          >
            <ArrowDown className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
