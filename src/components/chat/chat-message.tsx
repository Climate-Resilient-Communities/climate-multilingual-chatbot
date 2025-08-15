import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Bot, User } from "lucide-react";

export type Message = {
  role: 'user' | 'assistant';
  content: string;
};

type ChatMessageProps = {
  message: Message;
};

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  return (
    <div
      className={cn(
        "flex items-start gap-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <Avatar className="h-8 w-8">
          <AvatarFallback className="bg-primary text-primary-foreground">
            <Bot className="h-5 w-5" />
          </AvatarFallback>
        </Avatar>
      )}
      <div
        className={cn(
          "max-w-prose rounded-lg p-3 text-sm message-bubble",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content.split('**').map((part, index) => 
            index % 2 === 1 ? <strong key={index}>{part}</strong> : part
        )}</p>
      </div>
      {isUser && (
        <Avatar className="h-8 w-8">
          <AvatarFallback>
            <User className="h-5 w-5" />
          </AvatarFallback>
        </Avatar>
      )}
    </div>
  );
}
