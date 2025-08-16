
"use client";

import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import Image from "next/image";
import { type Source } from "@/components/chat/chat-message";

type CitationsPopoverProps = {
  sources: Source[];
};

function getFaviconUrl(url: string) {
    try {
        const urlObject = new URL(url);
        return `https://www.google.com/s2/favicons?domain=${urlObject.hostname}&sz=32`;
    } catch (error) {
        return "/fallback-favicon.png";
    }
}

export function CitationsPopover({ sources }: CitationsPopoverProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" className="h-7 gap-2 px-3 text-muted-foreground hover:text-foreground">
            <div className="flex -space-x-2">
                {sources.slice(0, 5).map((source, index) => (
                    <Image
                        key={index}
                        src={getFaviconUrl(source.url)}
                        alt="Source"
                        width={16}
                        height={16}
                        className="rounded-full border-2 border-background bg-white"
                    />
                ))}
            </div>
          <span className="text-xs">Sources</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[28rem]" align="start">
        <div className="space-y-2">
          <h4 className="font-semibold">Citations</h4>
          <ScrollArea className="h-72">
            <div className="p-1 flex flex-col">
                {sources.map((source, index) => (
                    <div key={index} className="border-b border-border last:border-b-0">
                        <a href={source.url} target="_blank" rel="noopener noreferrer" className="block p-4 space-y-2 rounded-lg hover:bg-muted/50 group">
                             <div className="flex items-center gap-3">
                                <Image
                                    src={getFaviconUrl(source.url)}
                                    alt={source.title}
                                    width={16}
                                    height={16}
                                    className="rounded-full"
                                />
                                <div className="text-xs text-muted-foreground">
                                    {new URL(source.url).hostname.replace('www.', '')}
                                </div>
                            </div>
                            <div className="text-sm font-medium text-foreground group-hover:underline">
                                {source.title}
                            </div>
                            <div className="text-xs text-foreground/80">
                                {source.text}
                            </div>
                        </a>
                    </div>
                ))}
            </div>
          </ScrollArea>
        </div>
      </PopoverContent>
    </Popover>
  );
}
