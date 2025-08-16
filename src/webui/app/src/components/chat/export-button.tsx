"use client";

import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import { ArrowUpToLine } from "lucide-react";
import { type Message } from "@/components/chat/chat-message";
import { useToast } from "@/hooks/use-toast";

type ExportButtonProps = {
  message: Message;
};

export function ExportButton({ message }: ExportButtonProps) {
  const isMobile = useIsMobile();
  const { toast } = useToast();

  const formatContent = () => {
    let content = `User: ${message.content}\n\n`;
    content += `Assistant: ${message.content}\n\n`;

    if (message.sources && message.sources.length > 0) {
      content += "Sources:\n";
      message.sources.forEach((source, index) => {
        content += `${index + 1}. ${source.title}\n`;
        content += `   URL: ${source.url}\n`;
        content += `   Details: ${source.text}\n\n`;
      });
    }
    return content;
  };

  const handleDownload = () => {
    const content = formatContent();
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "climate-chatbot-conversation.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleShare = async () => {
    const content = formatContent();
    if (navigator.share) {
      try {
        await navigator.share({
          title: "Climate Chatbot Conversation",
          text: content,
        });
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          // Do nothing if the user cancels the share sheet
          return;
        }
        if (error instanceof Error && error.name === 'NotAllowedError') {
          toast({
            variant: "destructive",
            title: "Sharing Failed",
            description: "This feature may require a secure (HTTPS) connection and user permission.",
          });
        } else {
          console.error("Error sharing:", error);
          toast({
            variant: "destructive",
            title: "An Unexpected Error Occurred",
            description: "Could not share the message.",
          });
        }
      }
    } else {
        toast({
            title: "Share Not Available",
            description: "Your browser does not support the Web Share API.",
        });
    }
  };

  const handleClick = isMobile ? handleShare : handleDownload;

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-7 w-7 text-muted-foreground hover:text-foreground"
      onClick={handleClick}
    >
      <ArrowUpToLine className="h-4 w-4" />
    </Button>
  );
}