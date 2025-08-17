
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
import { apiClient, type ChatRequest, type CitationDict, type LanguageDetectionRequest } from "@/lib/api";
import languagesData from "@/app/languages.json";

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
      // Smart language detection: only when default is English AND user writes in different language
      let finalLanguage = selectedLanguage;
      
      if (selectedLanguage === 'en') {
        let detectedLanguage = null;
        let confidence = 0;
        
        // First check: Common phrase detection for short messages across all languages
        const commonPhrasesByLanguage = {
          'es': ['hola', 'gracias', 'hasta luego', 'hasta la vista', 'buenas noches', 'buenos días', 'buenas tardes', 'por favor', 'de nada', 'lo siento', 'perdón', 'disculpe', 'ya me voy', 'nos vemos', 'adiós', 'chao', 'cómo estás', 'como estas', 'qué tal', 'que tal', 'muy bien', 'está bien', 'esta bien'],
          'fr': ['bonjour', 'salut', 'merci', 'au revoir', 'à bientôt', 'bonne nuit', 'bonne soirée', "s'il vous plaît", 'de rien', 'désolé', 'pardon', 'excusez-moi', 'comment allez-vous', 'comment ça va', 'ça va', 'très bien', 'ça marche'],
          'de': ['hallo', 'guten tag', 'danke', 'auf wiedersehen', 'tschüss', 'gute nacht', 'bitte', 'entschuldigung', 'wie geht es dir', 'wie gehts', 'gut', 'sehr gut'],
          'it': ['ciao', 'buongiorno', 'grazie', 'arrivederci', 'buonanotte', 'prego', 'scusa', 'come stai', 'come va', 'bene', 'molto bene'],
          'pt': ['olá', 'oi', 'obrigado', 'obrigada', 'tchau', 'até logo', 'boa noite', 'por favor', 'desculpa', 'como está', 'como vai', 'bem', 'muito bem'],
          'zh': ['你好', '谢谢', '再见', '晚安', '请', '对不起', '你怎么样', '很好'],
          'ja': ['こんにちは', 'ありがとう', 'さようなら', 'すみません', 'お元気ですか', 'はい'],
          'ko': ['안녕하세요', '감사합니다', '안녕히 가세요', '죄송합니다', '어떻게 지내세요', '좋습니다'],
          'ru': ['привет', 'спасибо', 'до свидания', 'пожалуйста', 'извините', 'как дела', 'хорошо'],
          'ar': ['مرحبا', 'شكرا', 'مع السلامة', 'من فضلك', 'آسف', 'كيف حالك', 'بخير'],
          'hi': ['नमस्ते', 'धन्यवाद', 'अलविदा', 'कृपया', 'माफ करें', 'आप कैसे हैं', 'अच्छा'],
          'nl': ['hallo', 'dank je', 'tot ziens', 'alsjeblieft', 'sorry', 'hoe gaat het', 'goed'],
          'sv': ['hej', 'tack', 'hej då', 'tack så mycket', 'ursäkta', 'hur mår du', 'bra'],
          'da': ['hej', 'tak', 'farvel', 'undskyld', 'hvordan har du det', 'godt'],
          'no': ['hei', 'takk', 'ha det', 'unnskyld', 'hvordan har du det', 'bra'],
          'fi': ['hei', 'kiitos', 'näkemiin', 'anteeksi', 'mitä kuuluu', 'hyvää'],
          'pl': ['cześć', 'dziękuję', 'do widzenia', 'przepraszam', 'jak się masz', 'dobrze'],
          'tr': ['merhaba', 'teşekkürler', 'güle güle', 'özür dilerim', 'nasılsın', 'iyi'],
          'he': ['שלום', 'תודה', 'להתראות', 'סליחה', 'איך אתה', 'טוב'],
          'th': ['สวัสดี', 'ขอบคุณ', 'ลาก่อน', 'ขอโทษ', 'สบายดีไหม', 'ดี'],
          'vi': ['xin chào', 'cảm ơn', 'tạm biệt', 'xin lỗi', 'bạn khỏe không', 'tốt'],
          'uk': ['привіт', 'дякую', 'до побачення', 'вибачте', 'як справи', 'добре'],
          'bg': ['здравей', 'благодаря', 'довиждане', 'извинете', 'как сте', 'добре'],
          'cs': ['ahoj', 'děkuji', 'na shledanou', 'promiňte', 'jak se máte', 'dobře'],
          'sk': ['ahoj', 'ďakujem', 'dovidenia', 'prepáčte', 'ako sa máte', 'dobre'],
          'hr': ['bok', 'hvala', 'doviđenja', 'oprostite', 'kako ste', 'dobro'],
          'sr': ['здраво', 'хвала', 'довиђења', 'извините', 'како сте', 'добро'],
          'sl': ['zdravo', 'hvala', 'nasvidenje', 'oprostite', 'kako ste', 'dobro'],
          'ro': ['salut', 'mulțumesc', 'la revedere', 'scuzați-mă', 'ce mai faceți', 'bine'],
          'hu': ['szia', 'köszönöm', 'viszlát', 'elnézést', 'hogy vagy', 'jól']
        };
        
        const queryLower = query.toLowerCase();
        
        // Check all languages for common phrases
        for (const [langCode, phrases] of Object.entries(commonPhrasesByLanguage)) {
          const hasPhrase = phrases.some(phrase => queryLower.includes(phrase));
          if (hasPhrase) {
            detectedLanguage = langCode;
            confidence = 0.9; // High confidence for known phrases
            break;
          }
        }
        
        if (!detectedLanguage) {
          // Second check: Use backend detection for longer/complex text
          try {
            const languageDetectionRequest: LanguageDetectionRequest = {
              query: query
            };
            
            const detectionResult = await apiClient.detectLanguage(languageDetectionRequest);
            detectedLanguage = detectionResult.detected_language;
            confidence = detectionResult.confidence;
          } catch (detectionError) {
            console.log('Language detection failed, using English:', detectionError);
          }
        }
        
        // If detected language is different from English and has good confidence
        if (detectedLanguage && detectedLanguage !== 'en' && confidence > 0.7) {
          // Auto-update the language dropdown
          setSelectedLanguage(detectedLanguage);
          finalLanguage = detectedLanguage;
          
          // Show a subtle notification about language detection
          const languageName = languagesData.speculative_supported_languages_nova_proxy.languages[detectedLanguage] || detectedLanguage;
          toast({
            title: "Language detected",
            description: `Automatically switched to ${languageName}. You can change this in the dropdown if needed.`,
            duration: 3000,
          });
        } else if (detectedLanguage && detectedLanguage !== 'en' && confidence <= 0.7) {
          // Low confidence detection - stay in English but show helpful message
          const errorMessageId = `language_help_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          setMessages((prev) => [...prev, { 
            role: "assistant", 
            content: "Hmm, we can't detect your language. To get started, please select your language from the menu and hit the 'Retry' button.",
            id: errorMessageId
          }]);
          setLoadingMessage(null);
          return; // Exit early to avoid making the API call
        } else if (!detectedLanguage || detectedLanguage === 'unknown') {
          // Backend couldn't detect language at all - check if query looks non-English
          const hasNonLatinChars = /[^\u0000-\u007F]/.test(query);
          const isShortQuery = query.trim().split(/\s+/).length <= 3;
          
          if (hasNonLatinChars || (isShortQuery && !query.toLowerCase().match(/\b(hello|hi|hey|what|how|is|the|and|of|to|in|for|with|on|at|from|by|about|into|through|during|before|after|above|below|up|down|out|off|over|under|again|further|then|once)\b/))) {
            // Likely non-English query that couldn't be detected
            const errorMessageId = `language_help_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            setMessages((prev) => [...prev, { 
              role: "assistant", 
              content: "Hmm, we can't detect your language. To get started, please select your language from the menu and hit the 'Retry' button.",
              id: errorMessageId
            }]);
            setLoadingMessage(null);
            return; // Exit early to avoid making the API call
          }
        }
      }

      // Convert message format for API
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const chatRequest: ChatRequest = {
        query,
        language: finalLanguage,
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
