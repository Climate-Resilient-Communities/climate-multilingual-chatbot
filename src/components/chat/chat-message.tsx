import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Copy, ThumbsDown, ThumbsUp, RefreshCw } from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
  } from "@/components/ui/dropdown-menu"

export type Message = {
  role: 'user' | 'assistant';
  content: string;
};

type ChatMessageProps = {
  message: Message;
};

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  const onCopy = () => {
    navigator.clipboard.writeText(message.content);
  }

  return (
    <div
      className={cn(
        "flex items-end gap-2",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
            "max-w-prose rounded-lg p-3 text-sm message-bubble",
            isUser
                ? "bg-primary text-primary-foreground rounded-br-none"
                : "bg-card text-card-foreground rounded-bl-none border"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content.split('**').map((part, index) => 
            index % 2 === 1 ? <strong key={index}>{part}</strong> : part
        )}</p>
        {!isUser && (
            <div className="flex items-center gap-2 mt-3 -mb-1">
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground" onClick={onCopy}>
                    <Copy className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground">
                    <ThumbsUp className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground">
                    <ThumbsDown className="h-4 w-4" />
                </Button>
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-7 gap-1 px-2 text-muted-foreground hover:text-foreground">
                            <RefreshCw className="h-4 w-4" />
                            <span className="text-sm">Retry</span>
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start">
                        <DropdownMenuItem>Option 1</DropdownMenuItem>
                        <DropdownMenuItem>Option 2</DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        )}
      </div>
    </div>
  );
}
