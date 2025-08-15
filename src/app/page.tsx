
"use client";

import { useState, FormEvent } from "react";
import { useToast } from "@/hooks/use-toast";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SendHorizonal } from "lucide-react";
import { AppHeader } from "@/app/components/chat/app-header";
import { ChatWindow } from "@/components/chat/chat-window";
import { ConsentDialog } from "@/components/chat/consent-dialog";
import { SampleQuestions } from "@/app/components/chat/sample-questions";
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

  const handleSendMessage = async (e: FormEvent<HTMLFormElement> | string) => {
    const isString = typeof e === 'string';
    if (!isString) {
      e.preventDefault();
    }
    
    const query = isString ? e : inputValue.trim();
    if (!query) return;

    setInputValue("");
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setIsLoading(true);

    // Mock response logic
    setTimeout(() => {
      let response = "I'm sorry, I can only respond to pre-set questions right now.";
      const lowerQuery = query.toLowerCase();

      if (lowerQuery.includes("local impacts")) {
        response = "In Toronto, local impacts of climate change include more frequent and intense heatwaves, increased risk of flooding from severe storms, and changes to ecosystems in local ravines and the Lake Ontario shoreline.";
      } else if (lowerQuery.includes("summer so hot")) {
        response = "Summers in Toronto are getting hotter due to the urban heat island effect, where buildings and pavement trap heat, combined with the broader effects of global warming, which raises baseline temperatures.";
      } else if (lowerQuery.includes("flooding")) {
        response = "To address flooding in Toronto, you can ensure your property has proper drainage, install a sump pump or backwater valve, use rain barrels to capture runoff, and support city-wide initiatives for green infrastructure like permeable pavements and green roofs.";
      } else if (lowerQuery.includes("carbon footprint")) {
        response = "You can reduce your carbon footprint by using public transit, cycling, or walking instead of driving; reducing home energy use with better insulation and energy-efficient appliances; and shifting to a more plant-based diet.";
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
    <div className="flex flex-col h-screen">
      <AppHeader onNewChat={handleNewChat} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <ChatWindow messages={messages} isLoading={isLoading} />
        {messages.length === 0 && !isLoading && (
            <SampleQuestions 
                onQuestionClick={(question) => handleSendMessage(question)} 
            />
        )}
      </div>
      
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
          <Button type="submit" size="icon" disabled={isLoading || !inputValue.trim()}>
            <SendHorizonal className="h-5 w-5" />
            <span className="sr-only">Send</span>
          </Button>
        </form>
      </div>
    </div>
  );
}
