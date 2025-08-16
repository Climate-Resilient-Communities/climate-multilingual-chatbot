
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Copy, ThumbsDown, ThumbsUp, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient, type FeedbackRequest } from "@/lib/api";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CitationsPopover, type Source } from "./citations-popover";
import { ExportButton } from "./export-button";
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
  id?: string; // Add optional ID for feedback tracking
  sources?: Source[]; // Add optional sources for citations
};

type ChatMessageProps = {
  message: Message;
  onRetry?: () => void; // Add retry callback
};

export function ChatMessage({ message, onRetry }: ChatMessageProps) {
  const [feedbackDialogOpen, setFeedbackDialogOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState<'up' | 'down' | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const { toast } = useToast();

  const isUser = message.role === 'user';

  const onCopy = () => {
    navigator.clipboard.writeText(message.content);
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
        toast({
          title: "Feedback submitted",
          description: `Thank you for your ${feedbackType === 'up' ? 'positive' : 'constructive'} feedback!`,
        });
        setFeedbackDialogOpen(false);
      } else {
        throw new Error("Failed to submit feedback");
      }
    } catch (error) {
      console.error('Feedback submission error:', error);
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

  return (
    <div
      className={cn(
        "flex items-start gap-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div className="flex flex-col items-start gap-2 max-w-prose">
        <div
            className={cn(
                "rounded-lg p-3 text-sm message-bubble border",
                isUser
                    ? "bg-primary text-primary-foreground rounded-br-none border-primary [&_*]:text-primary-foreground"
                    : "bg-card text-card-foreground rounded-bl-none border-border"
            )}
        >
            <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                        // Custom component styling to match the chat theme
                        h1: ({node, ...props}) => <h1 className="text-lg font-bold mb-2 text-foreground" {...props} />,
                        h2: ({node, ...props}) => <h2 className="text-base font-semibold mb-2 text-foreground" {...props} />,
                        h3: ({node, ...props}) => <h3 className="text-sm font-medium mb-1 text-foreground" {...props} />,
                        p: ({node, ...props}) => <p className="mb-2 last:mb-0 text-foreground" {...props} />,
                        ul: ({node, ...props}) => <ul className="list-disc list-inside mb-2 text-foreground" {...props} />,
                        ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-2 text-foreground" {...props} />,
                        li: ({node, ...props}) => <li className="mb-1 text-foreground" {...props} />,
                        strong: ({node, ...props}) => <strong className="font-semibold text-foreground" {...props} />,
                        em: ({node, ...props}) => <em className="italic text-foreground" {...props} />,
                        code: ({node, ...props}: any) => {
                            const inline = !props.className?.includes('language-');
                            return inline 
                                ? <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono text-foreground" {...props} />
                                : <code className="block bg-muted p-2 rounded text-xs font-mono text-foreground" {...props} />;
                        },
                        blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-muted-foreground/20 pl-4 italic text-muted-foreground" {...props} />,
                        a: ({node, ...props}) => <a className="text-primary hover:underline" {...props} />
                    }}
                >
                    {message.content}
                </ReactMarkdown>
            </div>
        </div>
        {!isUser && (
            <div className="flex items-center gap-1">
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground" onClick={onCopy}>
                    <Copy className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground" onClick={() => handleFeedback('up')}>
                    <ThumbsUp className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground" onClick={() => handleFeedback('down')}>
                    <ThumbsDown className="h-4 w-4" />
                </Button>
                <Button 
                    variant="ghost" 
                    className="h-7 gap-1 px-2 text-muted-foreground hover:text-foreground"
                    onClick={onRetry}
                    disabled={!onRetry}
                >
                    <RefreshCw className="h-4 w-4" />
                    <span className="text-xs">Retry</span>
                </Button>
                
                {message.sources && message.sources.length > 0 && <ExportButton message={message} />}

                {message.sources && message.sources.length > 0 && (
                    <CitationsPopover sources={message.sources} />
                )}
                
                {(!message.sources || message.sources.length === 0) && <ExportButton message={message} />}
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
                            id={option.id}
                            checked={selectedCategories.includes(option.id)}
                            onCheckedChange={(checked) => handleCategoryChange(option.id, checked as boolean)}
                        />
                        <Label htmlFor={option.id} className="font-normal">{option.label}</Label>
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
