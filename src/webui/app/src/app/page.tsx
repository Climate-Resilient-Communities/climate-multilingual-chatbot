
"use client";

import { useState, FormEvent, useRef, useEffect, useCallback } from "react";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Textarea as ShadcnTextarea } from "@/components/ui/textarea";
import Textarea from 'react-textarea-autosize';
import { ArrowUp, Square } from "lucide-react";
import { AppHeader } from "@/app/components/chat/app-header";
import { ChatWindow } from "@/components/chat/chat-window";
import { ConsentDialog } from "@/components/chat/consent-dialog";
import { type Message } from "@/components/chat/chat-message";
import { type Source } from "@/components/chat/citations-popover";
import { apiClient, type ChatRequest, type CitationDict, type LanguageDetectionRequest } from "@/lib/api";
import { detectLanguageByPhrases } from "@/lib/language-detection";
import languagesData from "@/app/languages.json";

// Map backend SSE progress stages to short user-facing status labels
const STAGE_LABELS: Record<string, string> = {
  initializing: "Thinking…",
  parsing_history: "Thinking…",
  detecting_language: "Detecting language…",
  retrieving_documents: "Searching verified sources…",
  generating_response: "Writing…",
};

const newId = (prefix: string) =>
  `${prefix}_${typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}_${Math.random().toString(36).slice(2, 11)}`}`;

export default function Home() {
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const [showConsent, setShowConsent] = useState(true);
  const [checkingConsent, setCheckingConsent] = useState(true);
  // Language selection state
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en');
  const [userManuallySelectedLanguage, setUserManuallySelectedLanguage] = useState<boolean>(false);
  const { toast } = useToast();

  const handleNewChat = () => {
    abortRef.current?.abort();
    setMessages([]);
    setIsStreaming(false);
    setSelectedLanguage('en'); // Always reset language to English for new chat
    setUserManuallySelectedLanguage(false);
  };

  const handleLanguageChange = (language: string) => {
    setSelectedLanguage(language);
    setUserManuallySelectedLanguage(true);
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

  const updateMessage = useCallback((id: string, patch: Partial<Message>) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }, []);

  const handleRetry = (messageIndex: number) => {
    // Find the last user message before this assistant message
    const userMessage = messages[messageIndex - 1];
    if (userMessage && userMessage.role === 'user') {
      // Remove the failed assistant message and retry
      setMessages(prev => prev.slice(0, messageIndex));
      handleSendMessage(userMessage.content, true); // Pass isRetry=true to prevent duplicate user message
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  /**
   * Resolve the language to send: honor a manual selection; otherwise try the
   * fast client-side phrase check, then the backend detector.
   */
  const resolveLanguage = async (query: string): Promise<string> => {
    if (selectedLanguage !== 'en' || userManuallySelectedLanguage) return selectedLanguage;

    let detectedLanguage: string | null = null;
    let confidence = 0;

    const phraseResult = detectLanguageByPhrases(query);
    if (phraseResult) {
      detectedLanguage = phraseResult.language;
      confidence = phraseResult.confidence;
    } else {
      try {
        const request: LanguageDetectionRequest = { query };
        const detectionResult = await apiClient.detectLanguage(request);
        detectedLanguage = detectionResult.detected_language;
        confidence = detectionResult.confidence;
      } catch {
        // Detection is best-effort — never a reason to block the message
      }
    }

    if (detectedLanguage && detectedLanguage !== 'en' && confidence > 0.5) {
      setSelectedLanguage(detectedLanguage);
      const languageName = (languagesData.speculative_supported_languages_nova_proxy.languages as any)[detectedLanguage] || detectedLanguage;
      toast({
        title: "Language detected",
        description: `Automatically switched to ${languageName}. You can change this in the dropdown if needed.`,
        duration: 3000,
      });
      return detectedLanguage;
    }
    return selectedLanguage;
  };

  const handleSendMessage = async (e: FormEvent<HTMLFormElement> | string, isRetry: boolean = false) => {
    const isString = typeof e === 'string';
    if (!isString) {
      e.preventDefault();
    }

    const query = isString ? e : inputValue.trim();
    if (!query || isStreaming) return;

    setInputValue("");

    if (!isRetry) {
      setMessages((prev) => [...prev, { role: "user", content: query, id: newId("user") }]);
    }

    // Conversation history as of before this turn
    const conversationHistory = messages.map(msg => ({ role: msg.role, content: msg.content }));

    // Placeholder the stream writes into — appears immediately as "Thinking…"
    const assistantId = newId("assistant");
    setMessages((prev) => [...prev, {
      role: "assistant",
      content: "",
      id: assistantId,
      streaming: true,
      statusLabel: "Thinking…",
    }]);
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    let receivedText = "";

    const finishWithError = (errorMessage: string) => {
      const msgLower = errorMessage.toLowerCase();
      // User errors (off-topic/harmful/language mismatch) read as a normal
      // assistant reply; system errors get a generic message plus a toast.
      const isUserError = msgLower.includes("climate change assistant") ||
                         msgLower.includes("only help with questions about climate") ||
                         msgLower.includes("i can't assist with that request") ||
                         msgLower.includes("i can't help with that") ||
                         msgLower.includes("language mismatch") ||
                         msgLower.includes("different language");

      updateMessage(assistantId, {
        content: isUserError
          ? errorMessage
          : "I'm sorry, I ran into a problem while answering. Please try again — and if it keeps happening, let us know through the feedback form.",
        streaming: false,
        statusLabel: undefined,
        isError: !isUserError,
      });

      if (!isUserError) {
        toast({ variant: "destructive", title: "Something went wrong", description: errorMessage });
      }
    };

    try {
      const finalLanguage = await resolveLanguage(query);

      const chatRequest: ChatRequest = {
        query,
        language: finalLanguage,
        conversation_history: conversationHistory,
        stream: true,
        skip_cache: isRetry
      };

      await new Promise<void>((resolve) => {
        apiClient.streamChatQuery(
          chatRequest,
          (data) => {
            if (data.type === 'progress' && !receivedText) {
              const label = STAGE_LABELS[data.stage];
              if (label) updateMessage(assistantId, { statusLabel: label });
            } else if (data.type === 'token') {
              receivedText = data.partial_response ?? (receivedText + (data.content ?? ""));
              updateMessage(assistantId, { content: receivedText, statusLabel: undefined });
            }
          },
          (response) => {
            const hasRealText = typeof response.response === 'string' && /\p{L}/u.test(response.response);
            if (hasRealText) {
              updateMessage(assistantId, {
                content: response.response,
                streaming: false,
                statusLabel: undefined,
                sources: response.citations.length > 0 ? convertCitationsToSources(response.citations) : undefined,
                retrieval_source: response.retrieval_source,
              });
            } else {
              finishWithError("The generated response was invalid. Please try again.");
            }
            resolve();
          },
          async (error) => {
            // Stream broke before completing. If we already have partial text,
            // keep it and let the user retry; otherwise fall back to the
            // non-streaming endpoint once before reporting an error.
            if (receivedText) {
              updateMessage(assistantId, { streaming: false, statusLabel: undefined });
              toast({
                variant: "destructive",
                title: "Connection interrupted",
                description: "The answer may be incomplete — use Retry to regenerate it.",
              });
            } else {
              try {
                const response = await apiClient.sendChatQuery({ ...chatRequest, stream: false });
                const hasRealText = response.success && typeof response.response === 'string' && /\p{L}/u.test(response.response);
                if (hasRealText) {
                  updateMessage(assistantId, {
                    content: response.response,
                    streaming: false,
                    statusLabel: undefined,
                    sources: response.citations.length > 0 ? convertCitationsToSources(response.citations) : undefined,
                    retrieval_source: response.retrieval_source,
                  });
                } else {
                  finishWithError(error.message);
                }
              } catch (fallbackError) {
                finishWithError(fallbackError instanceof Error ? fallbackError.message : error.message);
              }
            }
            resolve();
          },
          controller.signal
        );

        // A user-initiated stop resolves immediately: keep whatever streamed
        controller.signal.addEventListener('abort', () => {
          setMessages((prev) => prev
            .map((m) => (m.id === assistantId ? { ...m, streaming: false, statusLabel: undefined } : m))
            .filter((m) => !(m.id === assistantId && !receivedText)));
          resolve();
        });
      });
    } catch (error) {
      finishWithError(error instanceof Error ? error.message : "Failed to get response");
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
      inputRef.current?.focus();
    }
  };

  const handleConsent = async () => {
    try {
      await apiClient.acceptConsent();
      setShowConsent(false);
    } catch (error) {
      // Still allow the user to continue even if the API call fails
      setShowConsent(false);
      toast({
        variant: "destructive",
        title: "Warning",
        description: "Failed to save your consent preference. You may need to accept again on your next visit.",
        duration: 5000,
      });
    }
  };

  // Check consent on mount
  useEffect(() => {
    const checkConsent = async () => {
      try {
        const result = await apiClient.checkConsent();
        setShowConsent(!result.has_consent);
      } catch {
        setShowConsent(true);
      } finally {
        setCheckingConsent(false);
      }
    };

    checkConsent();
  }, []);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Show loading while checking consent
  if (checkingConsent) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (showConsent) {
    return <ConsentDialog open={showConsent} onConsent={handleConsent} />;
  }

  const canSend = inputValue.trim().length > 0 && !isStreaming;

  return (
    <div className="flex flex-col h-[100svh]">
      <AppHeader
        onNewChat={handleNewChat}
        selectedLanguage={selectedLanguage}
        onLanguageChange={handleLanguageChange}
      />
      <main className="flex-1 min-h-0">
        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          onQuestionClick={(question) => {
            handleSendMessage(question);
            inputRef.current?.focus();
          }}
          onRetry={handleRetry}
        />
      </main>

      <div className="shrink-0 border-t bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="mx-auto w-full max-w-3xl px-4 pb-3 pt-3 sm:px-6">
          <form
            onSubmit={handleSendMessage}
            className="flex items-end gap-1.5 rounded-2xl border bg-card p-1.5 pl-3 shadow-sm transition-shadow focus-within:border-primary/40 focus-within:shadow-md"
          >
            <ShadcnTextarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (canSend) handleSendMessage(inputValue);
                }
              }}
              placeholder="Ask about climate change…"
              aria-label="Ask about climate change"
              className="max-h-40 min-h-0 flex-1 resize-none border-0 bg-transparent px-0 py-2 text-[15px] shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
              minRows={1}
              maxRows={6}
              as={Textarea}
            />
            {isStreaming ? (
              <Button
                type="button"
                size="icon"
                variant="outline"
                onClick={handleStop}
                className="h-9 w-9 shrink-0 rounded-xl"
                aria-label="Stop generating"
                title="Stop generating"
              >
                <Square className="h-4 w-4 fill-current" />
              </Button>
            ) : (
              <Button
                type="submit"
                size="icon"
                disabled={!canSend}
                className="h-9 w-9 shrink-0 rounded-xl"
                aria-label="Send message"
                title="Send"
              >
                <ArrowUp className="h-5 w-5" />
              </Button>
            )}
          </form>
          <p className="mt-2 text-center text-[11px] leading-4 text-muted-foreground">
            Dunia can make mistakes — please check important information against the cited sources.
          </p>
        </div>
      </div>
    </div>
  );
}
