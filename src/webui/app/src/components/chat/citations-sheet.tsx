
"use client";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import Image from "next/image";
import { FileText } from "lucide-react";
import { type Source } from "@/components/chat/chat-message";

type CitationsSheetProps = {
  sources: Source[];
};

function isValidHttpUrl(string: string) {
  let url;
  try {
    url = new URL(string);
  } catch (_) {
    return false;
  }
  return url.protocol === "http:" || url.protocol === "https:";
}

function getFaviconUrl(url: string) {
    try {
        const urlObject = new URL(url);
        return `https://www.google.com/s2/favicons?domain=${urlObject.hostname}&sz=32`;
    } catch (error) {
        return ""; // Return empty for invalid URLs
    }
}

const SourceIcon = ({ url }: { url: string }) => {
    if (!isValidHttpUrl(url)) {
        return (
            <div className="flex h-[16px] w-[16px] items-center justify-center rounded-full border border-border bg-white">
                <FileText className="h-3 w-3 text-muted-foreground" />
            </div>
        );
    }
    const faviconUrl = getFaviconUrl(url);
    if (!faviconUrl) {
        return (
            <div className="flex h-[16px] w-[16px] items-center justify-center rounded-full border border-border bg-white">
                <FileText className="h-3 w-3 text-muted-foreground" />
            </div>
        );
    }
    return (
        <Image
            src={faviconUrl}
            alt="Source"
            width={16}
            height={16}
            className="rounded-full border border-border bg-white"
        />
    );
};

export function CitationsSheet({ sources }: CitationsSheetProps) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost" className="h-7 gap-2 px-3 text-muted-foreground hover:text-foreground">
            <div className="flex -space-x-2">
                {sources.slice(0, 5).reverse().map((source, index) => (
                    <SourceIcon key={index} url={source.url} />
                ))}
            </div>
          <span className="text-xs">Sources</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="bottom" className="h-[70svh]">
        <SheetHeader className="text-left">
          <SheetTitle>Citations</SheetTitle>
        </SheetHeader>
        <ScrollArea className="h-[calc(100%-4rem)]">
          <div className="p-1 flex flex-col mt-4">
              {sources.map((source, index) => {
                  const isUrl = isValidHttpUrl(source.url);
                  const SourceWrapper = isUrl ? 'a' : 'div';
                  
                  return (
                      <div key={index} className="border-b border-border last:border-b-0">
                          <SourceWrapper 
                              href={isUrl ? source.url : undefined} 
                              target={isUrl ? "_blank" : undefined} 
                              rel={isUrl ? "noopener noreferrer" : undefined} 
                              className="block p-4 space-y-2 rounded-lg hover:bg-muted/50 group"
                          >
                              <div className="flex items-center gap-3">
                                  {isUrl ? (
                                      <Image
                                          src={getFaviconUrl(source.url)}
                                          alt={source.title}
                                          width={16}
                                          height={16}
                                          className="rounded-full"
                                      />
                                  ) : (
                                      <FileText className="h-4 w-4 text-muted-foreground" />
                                  )}
                                  <div className="text-xs text-muted-foreground">
                                      {isUrl ? new URL(source.url).hostname.replace('www.', '') : 'PDF Document'}
                                  </div>
                              </div>
                              <div className="text-sm font-medium text-foreground group-hover:underline">
                                  {source.title}
                              </div>
                              <div className="text-xs text-foreground/80">
                                  {source.text}
                              </div>
                          </SourceWrapper>
                      </div>
                  );
              })}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
