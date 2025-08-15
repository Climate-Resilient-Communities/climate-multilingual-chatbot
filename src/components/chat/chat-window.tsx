"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage, type Message } from "@/components/chat/chat-message";
import { Loader2, Bot } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

type ChatWindowProps = {
  messages: Message[];
  isLoading: boolean;
};

export function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({
        top: scrollAreaRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages]);

  return (
    <div className="flex-1 overflow-hidden">
      <ScrollArea className="h-full" viewportRef={scrollAreaRef}>
        <div className="p-4 sm:p-6 space-y-6">
          {messages.length === 0 && !isLoading && (
            <Card className="max-w-lg mx-auto mt-20 border-0 shadow-none">
              <CardContent className="p-6 text-center flex flex-col items-center">
                  <Bot className="w-16 h-16 mb-4 text-primary/80"/>
                  <h2 className="text-xl font-semibold">Welcome to ClimateTalk!</h2>
                  <p className="text-muted-foreground mt-2 max-w-sm">
                      Ask me anything about climate change, and I'll provide you with information and local resources.
                  </p>
              </CardContent>
            </Card>
          )}
          {messages.map((msg, index) => (
            <ChatMessage key={index} message={msg} />
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-muted message-bubble">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">Thinking...</span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
