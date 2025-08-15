
"use client";

import { useState } from 'react';
import { Languages, Settings, MessageSquarePlus, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import languagesData from "@/app/languages.json";

type AppHeaderProps = {
  onNewChat: () => void;
};

export function AppHeader({ onNewChat }: AppHeaderProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const languages = languagesData.speculative_supported_languages_nova_proxy.languages;
  
  const sortedLanguages = Object.entries(languages)
    .sort(([, nameA], [, nameB]) => nameA.localeCompare(nameB));

  const englishIndex = sortedLanguages.findIndex(([code]) => code === 'en');
  const english = sortedLanguages.splice(englishIndex, 1)[0];
  sortedLanguages.unshift(english);

  return (
    <>
      <header className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-primary" />
            <h1 className="text-sm font-semibold text-muted-foreground">
                Multilingual Chatbot <span className="hidden sm:inline">• Made by Climate Resilient Communities</span>
            </h1>
        </div>
        <div className="flex items-center gap-2">
          <Select defaultValue="en">
            <SelectTrigger className="w-auto gap-2 text-sm h-9">
              <Languages className="h-4 w-4" />
              <SelectValue placeholder="Language" />
            </SelectTrigger>
            <SelectContent>
              {sortedLanguages.map(([code, name]) => (
                <SelectItem key={code} value={code}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={onNewChat} className="h-9">
            <MessageSquarePlus className="mr-2 h-4 w-4" />
            New Chat
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setSettingsOpen(true)} className="h-9 w-9">
            <Settings className="h-5 w-5" />
            <span className="sr-only">Settings</span>
          </Button>
        </div>
      </header>
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Settings</DialogTitle>
            <DialogDescription>
              Customize your experience.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              User settings will be available in a future version.
            </p>
          </div>
          <DialogFooter>
            <Button onClick={() => setSettingsOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
