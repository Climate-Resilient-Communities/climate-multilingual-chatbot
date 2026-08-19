
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
  const [showJump, setShowJump] = useState(false);

  // Auto-follow rules: a new message always scrolls into view; streamed
  // content only keeps the view pinned while the reader is already at the
  // bottom — scrolling up to read is never interrupted.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const isNewMessage = messages.length !== prevCountRef.current;
    prevCountRef.current = messages.length;

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
            <div className="flex flex-col items-center pt-10 text-center md:pt-24">
              <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/15">
                <Image src={Logo} alt="Dunia logo" width={40} height={40} className="h-10 w-10" />
              </div>
              <h1 className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
                Welcome to Dunia
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground md:text-[15px] md:leading-7">
                Dunia means &ldquo;world&rdquo; in Swahili — and I can chat in many of the
                world&rsquo;s languages. Pick yours from the menu above or just start typing.
                I answer with verified information and local resources, always with sources.
              </p>
              <div className="mt-10 w-full">
                <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Try asking
                </p>
                <SampleQuestions onQuestionClick={onQuestionClick} />
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg, index) => (
                <ChatMessage
                  key={msg.id || index}
                  message={msg}
                  onRetry={
                    msg.role === "assistant" && onRetry && index === lastAssistantIndex && !isStreaming
                      ? () => onRetry(index)
                      : undefined
                  }
                />
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
