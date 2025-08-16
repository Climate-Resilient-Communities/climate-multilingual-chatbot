
"use client";

import { useState } from 'react';
import Image from "next/image";
import Logo from "@/app/Logo.png";
import { Languages, HelpCircle, MessageSquarePlus, BarChart, Lock, ShieldCheck } from "lucide-react";
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
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import languagesData from "@/app/languages.json";

type AppHeaderProps = {
  onNewChat: () => void;
  selectedLanguage: string;
  onLanguageChange: (language: string) => void;
};

export function AppHeader({ onNewChat, selectedLanguage, onLanguageChange }: AppHeaderProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const languages = languagesData.speculative_supported_languages_nova_proxy.languages;
  
  const sortedLanguages = Object.entries(languages)
    .sort(([, nameA], [, nameB]) => nameA.localeCompare(nameB));

  const englishIndex = sortedLanguages.findIndex(([code]) => code === 'en');
  if (englishIndex > -1) {
    const english = sortedLanguages.splice(englishIndex, 1)[0];
    sortedLanguages.unshift(english);
  }

  return (
    <>
      <header className="flex items-center justify-between p-4 border-b">
        <a href="https://crc.place/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2">
            <Image src={Logo} alt="Climate Resilient Communities Logo" width={28} height={28} />
            <span className="hidden sm:inline text-sm font-semibold text-muted-foreground">
                Made by: Climate Resilient Communities™
            </span>
        </a>
        <div className="flex items-center gap-2">
          <Select value={selectedLanguage} onValueChange={onLanguageChange}>
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
            <HelpCircle className="h-5 w-5" />
            <span className="sr-only">FAQ</span>
          </Button>
        </div>
      </header>
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="max-h-[80svh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Support & FAQs</DialogTitle>
            <DialogDescription>
              Frequently Asked Questions
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 flex-1 overflow-y-auto pr-4 text-sm">
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="accuracy">
                <AccordionTrigger className="text-base">
                  <BarChart className="mr-2 h-5 w-5" /> Information Accuracy
                </AccordionTrigger>
                <AccordionContent className="space-y-4">
                  <div>
                    <p className="font-semibold">How accurate is the information provided by the chatbot?</p>
                    <p className="text-muted-foreground mt-1">
                      Our chatbot uses Retrieval-Augmented Generation (RAG) technology to provide verified information exclusively from government reports, academic research, and established non-profit organizations' publications. Every response includes citations to original sources, allowing you to verify the information directly. The system matches your questions with relevant, verified information rather than generating content independently.
                    </p>
                  </div>
                  <div>
                    <p className="font-semibold">What sources does the chatbot use?</p>
                    <p className="text-muted-foreground mt-1">
                      All information comes from three verified source types: government climate reports, peer-reviewed academic research, and established non-profit organization publications. Each response includes citations linking directly to these sources.
                    </p>
                  </div>
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="privacy">
                <AccordionTrigger className="text-base">
                  <Lock className="mr-2 h-5 w-5" /> Privacy Protection
                </AccordionTrigger>
                <AccordionContent className="space-y-4">
                  <div>
                    <p className="font-semibold">What information does the chatbot collect?</p>
                    <p className="text-muted-foreground mt-1">
                      We maintain a strict privacy-first approach:
                    </p>
                    <ul className="list-disc list-outside pl-5 mt-2 text-muted-foreground space-y-1">
                      <li>No personal identifying information (PII) is collected</li>
                      <li>Questions are automatically screened to remove any personal details</li>
                      <li>Only anonymized questions are cached to improve service quality</li>
                      <li>No user accounts or profiles are created</li>
                    </ul>
                  </div>
                  <div>
                    <p className="font-semibold">How is the cached data used?</p>
                    <p className="text-muted-foreground mt-1">
                      Cached questions, stripped of all identifying information, help us improve response accuracy and identify common climate information needs. We regularly delete cached questions after analysis.
                    </p>
                  </div>
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="trust">
                <AccordionTrigger className="text-base">
                  <ShieldCheck className="mr-2 h-5 w-5" /> Trust & Transparency
                </AccordionTrigger>
                <AccordionContent className="space-y-4">
                  <div>
                    <p className="font-semibold">How can I trust this tool?</p>
                     <p className="text-muted-foreground mt-1">
                      Our commitment to trustworthy information rests on:
                    </p>
                    <ul className="list-disc list-outside pl-5 mt-2 text-muted-foreground space-y-1">
                      <li>Citations for every piece of information, linking to authoritative sources</li>
                      <li>Open-source code available for public review on <a href="https://github.com/Climate-Resilient-Communities/climate-multilingual-chatbot" target="_blank" rel="noopener noreferrer" className="underline">GitHub</a></li>
                      <li>Community co-design ensuring real-world relevance</li>
                      <li>Regular updates based on user feedback and new research</li>
                    </ul>
                   </div>
                   <div>
                     <p className="font-semibold">How can I provide feedback or report issues?</p>
                     <p className="text-muted-foreground mt-1">
                      We welcome your input through:
                    </p>
                     <ul className="list-disc list-outside pl-5 mt-2 text-muted-foreground space-y-1">
                        <li>The feedback button within the chat interface</li>
                        <li>Our <a href="https://github.com/Climate-Resilient-Communities/climate-multilingual-chatbot" target="_blank" rel="noopener noreferrer" className="underline">GitHub repository</a> for technical contributions</li>
                        <li>Community feedback sessions</li>
                    </ul>
                    <a href="https://docs.google.com/forms/d/e/1FAIpQLSd2-iv25ZSpBkMuoz6dGgt8vuU1ifmi-PxY63I7accyAdHirg/viewform?pli=1" target="_blank" rel="noopener noreferrer">
                        <Button variant="outline" className="mt-4 w-full">Submit Feedback</Button>
                    </a>
                    <p className="text-muted-foreground mt-2 text-xs text-center">For technical support or to report issues, please visit our <a href="https://github.com/Climate-Resilient-Communities/climate-multilingual-chatbot" target="_blank" rel="noopener noreferrer" className="underline">GitHub repository</a>.</p>
                   </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </div>
          <DialogFooter>
            <Button onClick={() => setSettingsOpen(false)} className="w-full">Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

    