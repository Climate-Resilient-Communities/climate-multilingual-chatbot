"use client";

import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useState } from "react";
import { BookOpen, FileText, Globe } from "lucide-react";

export type Source = {
  url: string;
  title: string;
  text: string;
  content?: string;
  snippet?: string;
};

type CitationsPopoverProps = {
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

/**
 * Site favicon with a graceful fallback: when the favicon service is
 * unreachable (offline, blocked, invalid URL) a globe icon renders instead of
 * a broken image.
 */
export function SourceFavicon({ url }: { url: string }) {
    const [failed, setFailed] = useState(false);
    const faviconUrl = getFaviconUrl(url);

    if (failed || !faviconUrl) {
        return (
            <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-muted">
                <Globe className="h-3 w-3 text-muted-foreground" />
            </span>
        );
    }
    return (
        // eslint-disable-next-line @next/next/no-img-element
        <img
            src={faviconUrl}
            alt=""
            aria-hidden="true"
            width={16}
            height={16}
            className="h-4 w-4 shrink-0 rounded-full"
            onError={() => setFailed(true)}
        />
    );
}


export function CitationsPopover({ sources }: CitationsPopoverProps) {
  // DISABLED: URL validation was causing false positives due to CORS restrictions
  // const { validatedSources, isValidating } = useUrlValidation(sources, {
  //   autoValidate: true,
  //   showNotifications: false,
  //   validateOnMount: true,
  //   silentMode: true
  // });

  // Use original sources without validation to avoid false broken link warnings
  const displaySources = sources;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className="h-7 gap-1.5 rounded-full px-2.5 text-muted-foreground hover:text-foreground"
          title="View cited sources"
        >
          <BookOpen className="h-3.5 w-3.5" />
          <span className="text-xs font-medium">{displaySources.length} source{displaySources.length === 1 ? "" : "s"}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-96" align="center">
        <div className="space-y-2">
          <h4 className="font-semibold">Sources</h4>
          <ScrollArea className="h-72">
            <div className="p-1 flex flex-col">
                {displaySources.map((source, index) => {
                    const isUrl = isValidHttpUrl(source.url);
                    
                    return (
                        <div key={index} className="border-b border-border last:border-b-0">
                            {isUrl ? (
                                <a 
                                    href={source.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block p-4 space-y-2 rounded-lg hover:bg-muted/50 group"
                                >
                                    <div className="flex items-center gap-2">
                                        <SourceFavicon url={source.url} />
                                        <div className="truncate text-xs text-muted-foreground">
                                            {(() => {
                                                try {
                                                    return new URL(source.url).hostname.replace('www.', '');
                                                } catch {
                                                    return 'Web Source';
                                                }
                                            })()}
                                        </div>
                                    </div>
                                    <div className="text-sm font-medium text-foreground group-hover:underline">
                                        {source.title}
                                    </div>
                                    <div className="line-clamp-2 text-xs text-foreground/80">
                                        {source.text}
                                    </div>
                                </a>
                            ) : (
                                <div className="block p-4 space-y-2 rounded-lg">
                                    <div className="flex items-center gap-3">
                                        <FileText className="h-4 w-4 text-muted-foreground" />
                                        <div className="text-xs text-muted-foreground">
                                            PDF Document
                                        </div>
                                    </div>
                                    <div className="text-sm font-medium text-foreground">
                                        {source.title}
                                    </div>
                                    <div className="text-xs text-foreground/80">
                                        {source.text}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
          </ScrollArea>
        </div>
      </PopoverContent>
    </Popover>
  );
}