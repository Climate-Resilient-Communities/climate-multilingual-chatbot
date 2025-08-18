
"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import Logo from "@/app/Logo.png";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage, type Message } from "@/components/chat/chat-message";
import { Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { SampleQuestions } from "@/app/components/chat/sample-questions";

type ChatWindowProps = {
  messages: Message[];
  loadingMessage: string | null;
  onQuestionClick: (question: string) => void;
  onRetry?: (messageIndex: number) => void;
};

export function ChatWindow({ messages, loadingMessage, onQuestionClick, onRetry }: ChatWindowProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isLoading = loadingMessage !== null;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loadingMessage]);

  return (
    <div className="flex-1 overflow-hidden">
      <ScrollArea className="h-full" viewportRef={scrollAreaRef}>
        <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-6">
          {messages.length === 0 && !isLoading && (
            <div className="flex flex-col items-center justify-center h-full pt-10 md:pt-20">
              <Card className="max-w-3xl w-full mx-auto border-0 shadow-none bg-transparent">
                <CardContent className="p-6 text-center flex flex-col items-center">
                    <Image src={Logo} alt="Logo" width={64} height={64} className="w-16 h-16 mb-4" />
                    <h2 className="text-xl md:text-2xl font-semibold text-primary">Welcome to Multilingual Climate chatbot!</h2>
                    <p className="text-sm md:text-base text-muted-foreground mt-2 max-w-2xl">
                        I can chat in many languages. Select yours from the menu above to begin. Ask me anything about climate change, and I'll provide you with information and local resources.
                    </p>
                </CardContent>
              </Card>
              <SampleQuestions 
                  onQuestionClick={onQuestionClick} 
              />
            </div>
          )}
          {messages.map((msg, index) => (
            <ChatMessage 
              key={msg.id || index} 
              message={msg} 
              onRetry={msg.role === 'assistant' && onRetry ? () => onRetry(index) : undefined}
            />
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-muted message-bubble">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">{loadingMessage}</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
    </div>
  );
}
