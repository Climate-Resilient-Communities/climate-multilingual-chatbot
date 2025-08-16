
"use client";

import { useState, FormEvent, useRef, useEffect } from "react";
import Image from "next/image";
import Logo from "@/app/Logo.png";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Textarea as ShadcnTextarea } from "@/components/ui/textarea";
import Textarea from 'react-textarea-autosize';
import { SendHorizonal } from "lucide-react";
import { AppHeader } from "@/app/components/chat/app-header";
import { ChatWindow } from "@/components/chat/chat-window";
import { ConsentDialog } from "@/components/chat/consent-dialog";
import { type Message } from "@/components/chat/chat-message";
import { type Source } from "@/components/chat/citations-popover";
import { apiClient, type ChatRequest, type CitationDict } from "@/lib/api";

export default function Home() {
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);
  const [showConsent, setShowConsent] = useState(true);
  // Language selection state
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en');
  const { toast } = useToast();

  const handleNewChat = () => {
    setMessages([]);
  };

  const convertCitationsToSources = (citations: CitationDict[]): Source[] => {
    return citations.map((citation) => ({
      url: citation.url || '',
      title: citation.title || 'Untitled Source',
      text: citation.snippet || citation.content || '',
      content: citation.content,
      snippet: citation.snippet
    }));
  };

  const handleRetry = (messageIndex: number) => {
    // Find the last user message before this assistant message
    const userMessage = messages[messageIndex - 1];
    if (userMessage && userMessage.role === 'user') {
      // Remove the failed assistant message and retry
      setMessages(prev => prev.slice(0, messageIndex));
      handleSendMessage(userMessage.content);
    }
  };

  const handleSendMessage = async (e: FormEvent<HTMLFormElement> | string) => {
    const isString = typeof e === 'string';
    if (!isString) {
      e.preventDefault();
    }
    
    const query = isString ? e : inputValue.trim();
    if (!query) return;

    setInputValue("");
    const userMessageId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setMessages((prev) => [...prev, { role: "user", content: query, id: userMessageId }]);
    
    // Start with initial loading state
    setLoadingMessage("Thinking…");

    // High-level pipeline categories with realistic timing
    const pipelineStages = [
      { message: "Thinking…", delay: 1200 },           // Combines: initial setup, routing, rewriting, validation
      { message: "Retrieving documents…", delay: 1800 }, // Combines: document retrieval, relevance analysis  
      { message: "Formulating response…", delay: 2700 }, // Combines: LLM generation, quality verification
      { message: "Finalizing…", delay: 800 }             // Translation and final formatting
    ];

    // Show pipeline stages progressively
    let stageTimeouts: NodeJS.Timeout[] = [];
    let totalDelay = 0;

    pipelineStages.forEach((stage, index) => {
      totalDelay += stage.delay;
      const timeout = setTimeout(() => {
        setLoadingMessage(stage.message);
      }, totalDelay);
      stageTimeouts.push(timeout);
    });

    try {
      // Convert message format for API
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const chatRequest: ChatRequest = {
        query,
        language: selectedLanguage,
        conversation_history: conversationHistory,
        stream: false
      };
      
      const response = await apiClient.sendChatQuery(chatRequest);

      // Clear any remaining stage timeouts
      stageTimeouts.forEach(timeout => clearTimeout(timeout));
      
      if (response.success) {
        // Convert API citations to Source objects for the citations popover
        const sources: Source[] = response.citations.length > 0 
          ? convertCitationsToSources(response.citations)
          : [];
        
        const assistantMessageId = `assistant_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        setMessages((prev) => [...prev, { 
          role: "assistant", 
          content: response.response, // Keep original response without appended citations
          id: assistantMessageId,
          sources: sources // Add sources separately for citations popover
        }]);
        
        // Show success toast with processing info
        toast({
          title: "Response generated successfully",
          description: `Model: ${response.model_used} • Time: ${response.processing_time.toFixed(2)}s • Faithfulness: ${(response.faithfulness_score * 100).toFixed(1)}%`,
        });
      } else {
        throw new Error("API returned unsuccessful response");
      }
    } catch (error) {
      console.error('Chat API error:', error);
      
      // Clear any remaining stage timeouts on error
      stageTimeouts.forEach(timeout => clearTimeout(timeout));
      
      // Add error message to chat
      const errorMessageId = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setMessages((prev) => [...prev, { 
        role: "assistant", 
        content: "I'm sorry, I encountered an error while processing your request. Please try again or contact support if the issue persists.",
        id: errorMessageId
      }]);
      
      // Show error toast
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to get response",
      });
    } finally {
      setLoadingMessage(null);
    }
  };
  
  const handleConsent = () => {
    setShowConsent(false);
  };

  useEffect(() => {
    if (inputRef.current) {
        inputRef.current.focus();
    }
  }, []);

  if (showConsent) {
    return <ConsentDialog open={showConsent} onConsent={handleConsent} />;
  }
  
  const isLoading = loadingMessage !== null;

  return (
    <div className="flex flex-col h-[100svh]">
      <AppHeader 
        onNewChat={handleNewChat} 
        selectedLanguage={selectedLanguage}
        onLanguageChange={setSelectedLanguage}
      />
      <div className="flex-1 overflow-y-auto">
        <ChatWindow 
          messages={messages} 
          loadingMessage={loadingMessage}
          onQuestionClick={(question) => {
            handleSendMessage(question);
            if (inputRef.current) {
              inputRef.current.focus();
            }
          }}
          onRetry={handleRetry}
        />
      </div>
      
      <div className="p-4 border-t bg-background shrink-0">
        <form
          onSubmit={handleSendMessage}
          className="flex items-start gap-4 max-w-4xl mx-auto"
        >
          <Image src={Logo} alt="Logo" width={40} height={40} className="h-10 w-10 mt-0" />
          <ShadcnTextarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage(e as any);
              }
            }}
            placeholder="Ask about climate change..."
            className="flex-1 resize-none max-h-40"
            minRows={1}
            disabled={isLoading}
            as={Textarea}
          />
          <Button type="submit" size="icon" disabled={isLoading || !inputValue.trim()} className="self-end h-10 w-10">
            <SendHorizonal className="h-5 w-5" />
            <span className="sr-only">Send</span>
          </Button>
        </form>
      </div>
    </div>
  );
}
