
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
import { BookOpen, FileText } from "lucide-react";
import { SourceFavicon, type Source } from "@/components/chat/citations-popover";

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



export function CitationsSheet({ sources }: CitationsSheetProps) {
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
    <Sheet>
      <SheetTrigger asChild>
        <Button
          variant="outline"
          className="h-7 gap-1.5 rounded-full px-2.5 text-muted-foreground hover:text-foreground"
          title="View cited sources"
        >
          <BookOpen className="h-3.5 w-3.5" />
          <span className="text-xs font-medium">{displaySources.length} source{displaySources.length === 1 ? "" : "s"}</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="bottom" className="h-[70svh]">
        <SheetHeader className="text-left">
          <SheetTitle>Sources</SheetTitle>
        </SheetHeader>
        <ScrollArea className="h-[calc(100%-4rem)]">
          <div className="p-1 flex flex-col mt-4">
              {displaySources.map((source, index) => {
                  const isUrl = isValidHttpUrl(source.url);
                  const SourceWrapper = isUrl ? 'a' : 'div';
                  
                  return (
                      <div key={index} className="border-b border-border last:border-b-0">
                          <SourceWrapper 
                              href={SourceWrapper === 'a' ? source.url : undefined} 
                              target={SourceWrapper === 'a' ? "_blank" : undefined} 
                              rel={SourceWrapper === 'a' ? "noopener noreferrer" : undefined} 
                              className="block p-4 space-y-2 rounded-lg hover:bg-muted/50 group"
                          >
                              <div className="flex items-center gap-3">
                                  {isUrl ? (
                                      <SourceFavicon url={source.url} />
                                  ) : (
                                      <FileText className="h-4 w-4 text-muted-foreground" />
                                  )}
                                  <div className="text-xs text-muted-foreground">
                                      {isUrl ? (() => {
                                          try {
                                              return new URL(source.url).hostname.replace('www.', '');
                                          } catch {
                                              return 'Web Source';
                                          }
                                      })() : 'PDF Document'}
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
