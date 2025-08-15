"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Bot } from "lucide-react";

type ConsentDialogProps = {
  open: boolean;
  onConsent: () => void;
};

export function ConsentDialog({ open, onConsent }: ConsentDialogProps) {
  const [agreed, setAgreed] = useState(false);

  return (
    <Dialog open={open}>
      <DialogContent className="sm:max-w-lg" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
            <div className="flex justify-center mb-4">
                <Bot className="w-12 h-12 text-primary" />
            </div>
          <DialogTitle className="text-center text-2xl font-bold text-primary">MLCC Climate Chatbot</DialogTitle>
          <DialogDescription className="text-center">
            Your AI assistant for climate change information.
            <br />
            Connecting Toronto Communities to Climate Knowledge
          </DialogDescription>
        </DialogHeader>

        <p className="text-sm text-center text-muted-foreground mt-4">
          Welcome! This app shares clear info on climate impacts and local action. Please confirm you're good with the basics below.
        </p>

        <Accordion type="single" collapsible className="w-full my-4">
          <AccordionItem value="privacy">
            <AccordionTrigger>Privacy Policy</AccordionTrigger>
            <AccordionContent>
              <p className="text-sm text-muted-foreground">
                We value your privacy. We do not store your conversations. All data is processed in memory and is not used for training our models. We only collect anonymized usage statistics to improve our service.
              </p>
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="terms">
            <AccordionTrigger>Terms of Use</AccordionTrigger>
            <AccordionContent>
              <p className="text-sm text-muted-foreground">
                This service is provided under the MIT License. You are free to use it for any purpose, but the authors and copyright holders are not liable for any claims, damages, or other liability. Use the information provided at your own risk.
              </p>
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="disclaimer">
            <AccordionTrigger>Disclaimer</AccordionTrigger>
            <AccordionContent>
              <p className="text-sm text-muted-foreground">
                The information provided by this chatbot is for informational purposes only and does not constitute professional advice. While we strive for accuracy, we cannot guarantee it. Always consult with a qualified professional for specific advice.
              </p>
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <div className="flex items-center space-x-2">
          <Checkbox id="terms" checked={agreed} onCheckedChange={(checked) => setAgreed(checked as boolean)} />
          <Label htmlFor="terms" className="text-sm font-normal text-muted-foreground leading-none">
            By checking this box, you agree to our terms and policies.
          </Label>
        </div>

        <DialogFooter className="mt-4 sm:justify-center">
          <Button type="button" className="w-full" disabled={!agreed} onClick={onConsent}>
            Start Chatting Now
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
