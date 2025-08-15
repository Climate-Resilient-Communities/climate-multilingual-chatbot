"use client";

import { useState, useRef, FormEvent } from "react";
import { climateInfoRetrieval } from "@/ai/flows/climate-info-retrieval";
import { useToast } from "@/hooks/use-toast";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SendHorizonal } from "lucide-react";
import { AppHeader } from "@/components/chat/app-header";
import { ChatWindow } from "@/components/chat/chat-window";
import { ConsentDialog } from "@/components/chat/consent-dialog";
import { type Message } from "@/components/chat/chat-message";

export default function Home() {
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showConsent, setShowConsent] = useState(true);
  const { toast } = useToast();

  const handleNewChat = () => {
    setMessages([]);
    toast({
        title: "New chat started",
        description: "Your conversation history has been cleared.",
    });
  };

  const handleSendMessage = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const query = inputValue.trim().toLowerCase();
    if (!query) return;

    setInputValue("");
    setMessages((prev) => [...prev, { role: "user", content: inputValue.trim() }]);
    setIsLoading(true);

    // Mock response logic
    setTimeout(() => {
      let response = "";
      if (query === "hello") {
        response = "hello im your climate chatbot how can i help you";
      } else if (query === "what is climage change?") {
        response = "climate change is..... ";
      } else {
        setMessages((prev) => [...prev, { role: "assistant", content: "I'm sorry, I can only respond to 'hello' and 'what is climage change?' right now." }]);
        setIsLoading(false);
        return;
      }
      setMessages((prev) => [...prev, { role: "assistant", content: response }]);
      setIsLoading(false);
    }, 1000);
  };
  
  const handleConsent = () => {
    setShowConsent(false);
  };

  if (showConsent) {
    return <ConsentDialog open={showConsent} onConsent={handleConsent} />;
  }

  return (
    <div className="flex flex-col h-screen bg-background">
      <AppHeader onNewChat={handleNewChat} />
      <ChatWindow messages={messages} isLoading={isLoading} />
      <div className="p-4 border-t bg-background">
        <form
          onSubmit={handleSendMessage}
          className="flex items-center gap-2 max-w-2xl mx-auto"
        >
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask about climate change..."
            className="flex-1"
            disabled={isLoading}
          />
          <Button type="submit" size="icon" disabled={isLoading || !inputValue}>
            <SendHorizonal className="h-5 w-5" />
            <span className="sr-only">Send</span>
          </Button>
        </form>
      </div>
    </div>
  );
}
