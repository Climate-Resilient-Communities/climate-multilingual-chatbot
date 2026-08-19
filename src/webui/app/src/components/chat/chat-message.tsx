
"use client";

import { useState } from "react";
import Image from "next/image";
import Logo from "@/app/Logo.png";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Check, Copy, ThumbsDown, ThumbsUp, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient, type FeedbackRequest } from "@/lib/api";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CitationsPopover, type Source } from "./citations-popover";
import { CitationsSheet } from "./citations-sheet";
import { ExportButton } from "./export-button";
import { useIsMobile } from "@/hooks/use-mobile";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export type Message = {
  role: 'user' | 'assistant';
  content: string;
  id?: string; // Optional ID for feedback tracking
  sources?: Source[]; // Optional sources for citations
  retrieval_source?: string; // Optional retrieval source for canned responses
  streaming?: boolean; // True while this message is still being generated
  statusLabel?: string; // Pipeline status shown before the first token arrives
  isError?: boolean; // True when this message reports a system error
};

type ChatMessageProps = {
  message: Message;
  onRetry?: () => void;
};

function ThinkingIndicator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2.5 py-0.5" role="status" aria-label={label}>
      <span className="flex items-center gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/70 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/70 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/70" />
      </span>
      <span className="text-sm text-muted-foreground">{label}</span>
    </div>
  );
}

export function ChatMessage({ message, onRetry }: ChatMessageProps) {
  const [feedbackDialogOpen, setFeedbackDialogOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState<'up' | 'down' | null>(null);
  const [feedbackGiven, setFeedbackGiven] = useState<'up' | 'down' | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [copied, setCopied] = useState(false);
  const { toast } = useToast()
  const isMobile = useIsMobile()
  const hasSources = !!message.sources && message.sources.length > 0;

  const isUser = message.role === 'user';

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast({ variant: "destructive", title: "Copy failed", description: "Couldn't access the clipboard." });
    }
  }

  const handleFeedback = (type: 'up' | 'down') => {
    setFeedbackType(type);
    setSelectedCategories([]);
    setFeedbackComment('');
    setFeedbackDialogOpen(true);
  };

  const handleCategoryChange = (categoryId: string, checked: boolean) => {
    setSelectedCategories(prev =>
      checked
        ? [...prev, categoryId]
        : prev.filter(id => id !== categoryId)
    );
  };

  const submitFeedback = async () => {
    if (!feedbackType || !message.id) return;

    setIsSubmittingFeedback(true);
    try {
      const feedbackRequest: FeedbackRequest = {
        message_id: message.id,
        feedback_type: feedbackType === 'up' ? 'thumbs_up' : 'thumbs_down',
        categories: selectedCategories,
        comment: feedbackComment.trim() || undefined,
        language_code: 'en'
      };

      const response = await apiClient.submitFeedback(feedbackRequest);

      if (response.success) {
        setFeedbackGiven(feedbackType);
        setFeedbackDialogOpen(false);
        toast({ title: "Thanks for the feedback!", duration: 2000 });
      } else {
        throw new Error("Failed to submit feedback");
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to submit feedback. Please try again.",
      });
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const thumbsUpOptions = [
    { id: "instructions", label: "Followed Instructions" },
    { id: "comprehensive", label: "Comprehensive Answer" },
    { id: "translation", label: "Good Translation" },
    { id: "expected", label: "Response works as expected" },
    { id: "other", label: "Other" },
  ];

  const thumbsDownOptions = [
    { id: "instructions", label: "Didn't follow instructions" },
    { id: "no-response", label: "No Response Generated" },
    { id: "unrelated", label: "Response Unrelated" },
    { id: "translation", label: "Bad Translation" },
    { id: "guard-filter", label: "Guard Filter Misclassified" },
    { id: "other", label: "Other" },
  ];

  const feedbackOptions = feedbackType === 'up' ? thumbsUpOptions : thumbsDownOptions;

  // --- User message: compact right-aligned bubble, plain text ---
  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="message-bubble max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-[15px] leading-relaxed text-primary-foreground shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  // --- Assistant message: avatar + content card + action row ---
  const showThinking = !!message.streaming && !message.content && !!message.statusLabel;

  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/15">
        <Image src={Logo} alt="Dunia" width={20} height={20} className="h-5 w-5" />
      </div>

      <div className="min-w-0 flex-1">
        <div
          className={cn(
            "message-bubble rounded-2xl rounded-tl-md border bg-card px-4 py-3 shadow-sm",
            message.isError && "border-destructive/30 bg-destructive/5"
          )}
        >
          {showThinking ? (
            <ThinkingIndicator label={message.statusLabel!} />
          ) : (
            <div className="chat-markdown min-w-0" data-streaming={message.streaming ? "true" : undefined}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    h1: ({node, ...props}) => <h1 className="mb-2 mt-4 text-xl font-semibold tracking-tight text-foreground first:mt-0" {...props} />,
                    h2: ({node, ...props}) => <h2 className="mb-2 mt-4 text-lg font-semibold tracking-tight text-foreground first:mt-0" {...props} />,
                    h3: ({node, ...props}) => <h3 className="mb-1.5 mt-3 text-[15px] font-semibold text-foreground first:mt-0" {...props} />,
                    p: ({node, ...props}) => <p className="mb-2.5 text-[15px] leading-7 text-foreground last:mb-0" {...props} />,
                    ul: ({node, ...props}) => <ul className="mb-2.5 list-disc space-y-1 pl-5 text-[15px] leading-7 text-foreground marker:text-primary/60 last:mb-0" {...props} />,
                    ol: ({node, ...props}) => <ol className="mb-2.5 list-decimal space-y-1 pl-5 text-[15px] leading-7 text-foreground marker:font-medium marker:text-muted-foreground last:mb-0" {...props} />,
                    li: ({node, ...props}) => <li className="pl-1 [&>p]:mb-1" {...props} />,
                    strong: ({node, ...props}) => <strong className="font-semibold text-foreground" {...props} />,
                    em: ({node, ...props}) => <em className="italic" {...props} />,
                    table: ({node, ...props}) => (
                        <div className="my-3 overflow-x-auto rounded-lg border">
                            <table className="w-full border-collapse text-sm [&_tr:last-child_td]:border-b-0" {...props} />
                        </div>
                    ),
                    thead: ({node, ...props}) => <thead className="bg-muted/60" {...props} />,
                    th: ({node, ...props}) => <th className="border-b px-3 py-2 text-left text-[13px] font-semibold text-foreground" {...props} />,
                    td: ({node, ...props}) => <td className="border-b border-border/70 px-3 py-2 align-top text-foreground" {...props} />,
                    code: ({node, ...props}: any) => {
                        const inline = !props.className?.includes('language-');
                        return inline
                            ? <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[13px] text-foreground" {...props} />
                            : <code className="my-2 block overflow-x-auto rounded-lg bg-muted p-3 font-mono text-[13px] text-foreground" {...props} />;
                    },
                    blockquote: ({node, ...props}) => <blockquote className="my-2 border-l-2 border-primary/40 pl-3 italic text-muted-foreground" {...props} />,
                    hr: ({node, ...props}) => <hr className="my-3 border-border" {...props} />,
                    a: ({node, ...props}) => <a className="font-medium text-primary underline decoration-primary/40 underline-offset-2 hover:decoration-primary" target="_blank" rel="noopener noreferrer" {...props} />
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {!message.streaming && !showThinking && (
            <div className="mt-1.5 flex flex-wrap items-center gap-0.5">
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground hover:text-foreground"
                    onClick={onCopy}
                    aria-label={copied ? "Copied" : "Copy answer"}
                    title={copied ? "Copied!" : "Copy"}
                >
                    {copied ? <Check className="h-4 w-4 text-primary" /> : <Copy className="h-4 w-4" />}
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className={cn("h-7 w-7 text-muted-foreground hover:text-foreground", feedbackGiven === 'up' && "text-primary hover:text-primary")}
                    onClick={() => handleFeedback('up')}
                    aria-label="Good answer"
                    title="Good answer"
                >
                    <ThumbsUp className={cn("h-4 w-4", feedbackGiven === 'up' && "fill-current")} />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className={cn("h-7 w-7 text-muted-foreground hover:text-foreground", feedbackGiven === 'down' && "text-destructive hover:text-destructive")}
                    onClick={() => handleFeedback('down')}
                    aria-label="Poor answer"
                    title="Poor answer"
                >
                    <ThumbsDown className={cn("h-4 w-4", feedbackGiven === 'down' && "fill-current")} />
                </Button>
                {onRetry && (
                    <Button
                        variant="ghost"
                        className="h-7 gap-1 px-2 text-muted-foreground hover:text-foreground"
                        onClick={onRetry}
                        title="Regenerate this answer"
                    >
                        <RefreshCw className="h-4 w-4" />
                        <span className="text-xs">Retry</span>
                    </Button>
                )}

                {hasSources && message.retrieval_source !== "canned" && <ExportButton message={message} />}

                {hasSources && (
                    isMobile
                        ? <CitationsSheet sources={message.sources!} />
                        : <CitationsPopover sources={message.sources!} />
                )}

                {!hasSources && message.retrieval_source !== "canned" && !message.isError && <ExportButton message={message} />}
            </div>
        )}
      </div>

      <Dialog open={feedbackDialogOpen} onOpenChange={setFeedbackDialogOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
                {feedbackType === 'up' && <ThumbsUp className="h-5 w-5" />}
                {feedbackType === 'down' && <ThumbsDown className="h-5 w-5" />}
                Why did you choose this rating?
            </DialogTitle>
            <DialogDescription>
              (Optional)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-3">
                {feedbackOptions.map(option => (
                    <div key={option.id} className="flex items-center space-x-2">
                        <Checkbox
                            id={`${message.id || 'msg'}-${option.id}`}
                            checked={selectedCategories.includes(option.id)}
                            onCheckedChange={(checked) => handleCategoryChange(option.id, checked as boolean)}
                        />
                        <Label htmlFor={`${message.id || 'msg'}-${option.id}`} className="font-normal">{option.label}</Label>
                    </div>
                ))}
            </div>
            <Textarea
                placeholder="Provide additional feedback"
                value={feedbackComment}
                onChange={(e) => setFeedbackComment(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button
                variant="outline"
                onClick={() => setFeedbackDialogOpen(false)}
                disabled={isSubmittingFeedback}
            >
                Cancel
            </Button>
            <Button
                onClick={submitFeedback}
                disabled={isSubmittingFeedback}
            >
                {isSubmittingFeedback ? 'Submitting...' : 'Submit'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
