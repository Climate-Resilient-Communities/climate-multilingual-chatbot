
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Copy, ThumbsDown, ThumbsUp, RefreshCw } from "lucide-react";
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
import { CitationsPopover } from "./citations-popover";


export type Source = {
    url: string;
    title: string;
    text: string;
};

export type Message = {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
};

type ChatMessageProps = {
  message: Message;
};

export function ChatMessage({ message }: ChatMessageProps) {
  const [feedbackDialogOpen, setFeedbackDialogOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState<'up' | 'down' | null>(null);

  const isUser = message.role === 'user';

  const onCopy = () => {
    navigator.clipboard.writeText(message.content);
  }

  const handleFeedback = (type: 'up' | 'down') => {
    setFeedbackType(type);
    setFeedbackDialogOpen(true);
  }

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
                    ? "bg-primary text-primary-foreground rounded-br-none border-primary"
                    : "bg-card text-card-foreground rounded-bl-none border-border"
            )}
        >
            <p className="whitespace-pre-wrap">{message.content.split('**').map((part, index) => 
                index % 2 === 1 ? <strong key={index}>{part}</strong> : part
            )}</p>
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
                <Button variant="ghost" className="h-7 gap-1 px-2 text-muted-foreground hover:text-foreground">
                    <RefreshCw className="h-4 w-4" />
                    <span className="text-xs">Retry</span>
                </Button>
                {message.sources && message.sources.length > 0 && (
                    <CitationsPopover sources={message.sources} />
                )}
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
                        <Checkbox id={option.id} />
                        <Label htmlFor={option.id} className="font-normal">{option.label}</Label>
                    </div>
                ))}
            </div>
            <Textarea placeholder="Provide additional feedback" />
          </div>
          <DialogFooter>
            <Button onClick={() => setFeedbackDialogOpen(false)}>Submit</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
