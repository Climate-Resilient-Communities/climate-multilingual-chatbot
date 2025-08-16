
"use client";

import { useState, FormEvent, useRef, useEffect } from "react";
import Image from "next/image";
import Logo from "@/app/Logo.png";
import Textarea from "react-textarea-autosize";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { SendHorizonal } from "lucide-react";
import { AppHeader } from "@/app/components/chat/app-header";
import { ChatWindow } from "@/components/chat/chat-window";
import { ConsentDialog } from "@/components/chat/consent-dialog";
import { type Message, type Source } from "@/components/chat/chat-message";
import { Textarea as ShadcnTextarea } from "@/components/ui/textarea";

const mockSources: Record<string, Source[]> = {
  local_impacts: [
    { url: "TransformTO_Net_Zero_Strategy.pdf", title: "TransformTO Net Zero Strategy", text: "Toronto's climate action plan outlines strategies to reduce emissions and adapt to climate change." },
    { url: "Toronto_Future_Weather_Climate_Driver_Study.pdf", title: "Toronto's Future Weather & Climate Driver Study", text: "A study on the future weather and climate projections for the City of Toronto." },
    { url: "https://cleanairpartnership.org/wp-content/uploads/2021/08/Toronto-Case-Study-GTHA-2021.pdf", title: "City of Toronto Case Study on Climate Adaptation", text: "Details on how Toronto is building resilience to climate change impacts." },
    { url: "Ontario_Climate_Change_Impact_Assessment.pdf", title: "Ontario Climate Change Impact Assessment", text: "Provincial-level assessment of climate change impacts in Ontario." },
    { url: "https://www.nrcan.gc.ca/our-natural-resources/climate-change/climate-change-impacts-adaptation/regional-perspectives/ontario/21018", title: "Natural Resources Canada - Ontario Climate Change", text: "An overview of climate change impacts in the Ontario region." },
  ],
  summer_hot: [
    { url: "https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/urban-heat-island-effect/", title: "Urban Heat Island Effect in Toronto", text: "Information on why urban areas like Toronto get hotter than surrounding rural areas." },
    { url: "https://www.canada.ca/en/health-canada/services/environmental-workplace-health/climate-change-health/heat-illness/urban-heat-island-effect.html", title: "Health Canada: Urban Heat Island Effect", text: "Explains the health risks associated with the urban heat island effect." },
    { url: "https://climate.nasa.gov/effects/", title: "NASA: Global Climate Change Effects", text: "Overview of global warming from NASA, a key driver of rising temperatures." },
    { url: "https://www.ipcc.ch/report/ar6/syr/", title: "IPCC Sixth Assessment Report", text: "The definitive scientific report on the state of global climate change." },
    { url: "https://www.sciencedirect.com/science/article/pii/S221260901930107X", title: "Study on Urban Heat Islands and Climate Change", text: "Academic paper discussing the combined impact of urban heat islands and global warming." },
  ],
  flooding: [
    { url: "https://www.toronto.ca/services-payments/water-environment/managing-rain-stormwater/basement-flooding-protection-program/", title: "Basement Flooding Protection Program", text: "The City of Toronto's program to help residents protect their homes from flooding." },
    { url: "https://www.intactcentre.ca/", title: "Intact Centre on Climate Adaptation", text: "Resources and guidance on protecting homes and communities from flooding." },
    { url: "https://www.trca.ca/conservation/flood-risk-management/", title: "Toronto and Region Conservation Authority (TRCA) - Flood Risk Management", text: "Information on floodplains and flood risk management in the Toronto region." },
    { url: "https://www.canada.ca/en/environment-climate-change/services/water-overview/quantity-quality/floods.html", title: "Government of Canada - Flooding Information", text: "Federal government resources on flood preparedness and safety." },
    { url: "https://www.greeninfrastructureontario.org/", title: "Green Infrastructure Ontario", text: "Information on how green infrastructure like green roofs and permeable pavement can reduce flood risk." },
  ],
  carbon_footprint: [
    { url: "https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/green-your-transportation/", title: "Green Your Transportation", text: "City of Toronto tips for reducing your transportation-related carbon footprint." },
    { url: "https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/home-energy-loan-program-help/", title: "Home Energy Loan Program (HELP)", text: "A City of Toronto program to help homeowners improve energy efficiency." },
    { url: "https://davidsuzuki.org/what-you-can-do/top-10-ways-can-stop-climate-change/", title: "David Suzuki Foundation: Top 10 Ways to Stop Climate Change", text: "Actionable tips for reducing your personal carbon footprint." },
    { url: "https://www.un.org/en/actnow/ten-actions", title: "United Nations: ActNow - 10 Actions", text: "The UN's campaign for individual action on climate change and sustainability." },
    { url: "https://www.nature.org/en-us/get-involved/how-to-help/carbon-footprint-calculator/", title: "The Nature Conservancy Carbon Footprint Calculator", text: "A tool to calculate your carbon footprint and find ways to reduce it." },
  ],
};


export default function Home() {
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);
  const [showConsent, setShowConsent] = useState(true);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleNewChat = () => {
    setMessages([]);
  };

  const handleSendMessage = async (e: FormEvent<HTMLFormElement> | string) => {
    const isString = typeof e === 'string';
    if (!isString) {
      e.preventDefault();
    }
    
    const query = isString ? e : inputValue.trim();
    if (!query) return;

    setInputValue("");
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    
    const loadingStates = [
        "Thinking…",
        "Retrieving documents…",
        "Generating response…",
        "Finalizing…",
    ];
    let stateIndex = 0;
    setLoadingMessage(loadingStates[stateIndex]);

    const interval = setInterval(() => {
        stateIndex++;
        if (stateIndex < loadingStates.length) {
            setLoadingMessage(loadingStates[stateIndex]);
        }
    }, 300);

    // Mock response logic
    setTimeout(() => {
      clearInterval(interval);
      let response = "I'm sorry, I can only respond to pre-set questions right now.";
      let sources: Source[] = [];
      const lowerQuery = query.toLowerCase();

      if (lowerQuery.includes("hello")) {
        response = "Hello! I'm the Multilingual Climate Chatbot (MLCC). How can I help you today?";
        sources = [];
      } else if (lowerQuery.includes("local impacts")) {
        response = "In Toronto, local impacts of climate change include more frequent and intense heatwaves, increased risk of flooding from severe storms, and changes to ecosystems in local ravines and the Lake Ontario shoreline.";
        sources = mockSources.local_impacts;
      } else if (lowerQuery.includes("summer so hot")) {
        response = "Summers in Toronto are getting hotter due to the urban heat island effect, where buildings and pavement trap heat, combined with the broader effects of global warming, which raises baseline temperatures.";
        sources = mockSources.summer_hot;
      } else if (lowerQuery.includes("flooding")) {
        response = "To address flooding in Toronto, you can ensure your property has proper drainage, install a sump pump or backwater valve, use rain barrels to capture runoff, and support city-wide initiatives for green infrastructure like permeable pavements and green roofs.";
        sources = mockSources.flooding;
      } else if (lowerQuery.includes("carbon footprint")) {
        response = "You can reduce your carbon footprint by using public transit, cycling, or walking instead of driving; reducing home energy use with better insulation and energy-efficient appliances; and shifting to a more plant-based diet.";
        sources = mockSources.carbon_footprint;
      }
      
      setMessages((prev) => [...prev, { role: "assistant", content: response, sources: sources }]);
      setLoadingMessage(null);
    }, 1200);
  };
  
  const handleConsent = () => {
    setShowConsent(false);
  };

  useEffect(() => {
    if (inputRef.current) {
        inputRef.current.focus();
    }
  }, []);

  if (showConsent) {
    return <ConsentDialog open={showConsent} onConsent={handleConsent} />;
  }
  
  const isLoading = loadingMessage !== null;

  return (
    <div className="flex flex-col h-[100svh] bg-background">
      <AppHeader onNewChat={handleNewChat} />
      <div className="flex-1 overflow-y-auto">
        <ChatWindow 
          messages={messages} 
          loadingMessage={loadingMessage}
          onQuestionClick={(question) => {
              handleSendMessage(question);
              if (inputRef.current) {
                  inputRef.current.focus();
              }
          }}
        />
      </div>
      
      <div className="p-4 border-t bg-background shrink-0">
        <form
          onSubmit={handleSendMessage}
          className="flex items-start gap-4 max-w-4xl mx-auto"
        >
          <Image src={Logo} alt="Logo" width={40} height={40} className="h-10 w-10 mt-0" />
          <ShadcnTextarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e as any);
                }
            }}
            placeholder="Ask about climate change..."
            className="flex-1 resize-none max-h-40"
            minRows={1}
            disabled={isLoading}
            as={Textarea}
          />
          <Button type="submit" size="icon" disabled={isLoading || !inputValue.trim()} className="self-end h-10 w-10">
            <SendHorizonal className="h-5 w-5" />
            <span className="sr-only">Send</span>
          </Button>
        </form>
      </div>
    </div>
  );
}
