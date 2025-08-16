
"use client";

import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import { ArrowUpToLine, Share2 } from "lucide-react";
import { type Message } from "@/components/chat/chat-message";

type ExportButtonProps = {
  message: Message;
};

export function ExportButton({ message }: ExportButtonProps) {
  const isMobile = useIsMobile();

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
        console.error("Error sharing:", error);
      }
    }
  };

  if (isMobile) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7 text-muted-foreground hover:text-foreground"
        onClick={handleShare}
      >
        <Share2 className="h-4 w-4" />
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-7 w-7 text-muted-foreground hover:text-foreground"
      onClick={handleDownload}
    >
      <ArrowUpToLine className="h-4 w-4" />
    </Button>
  );
}
