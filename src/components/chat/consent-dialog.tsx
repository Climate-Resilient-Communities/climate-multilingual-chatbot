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
      <DialogContent className="sm:max-w-md" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
            <div className="flex justify-center mb-4">
                <Bot className="w-12 h-12 text-primary" />
            </div>
          <DialogTitle className="text-center text-xl font-bold text-primary">MLCC Climate Chatbot</DialogTitle>
          <DialogDescription className="text-center text-muted-foreground !mt-2">
            Connecting Toronto Communities to Climate Knowledge
          </DialogDescription>
        </DialogHeader>

        <div className="my-2 space-y-2">
            <p className="text-sm text-center text-muted-foreground">
              Welcome! This app shares clear info on climate impacts and local action. Please confirm you're good with the basics below.
            </p>

            <div className="flex items-start space-x-3 pt-2">
              <Checkbox id="terms" checked={agreed} onCheckedChange={(checked) => setAgreed(checked as boolean)} className="mt-1" />
              <Label htmlFor="terms" className="text-sm font-medium leading-none text-foreground">
                  By checking this box, you agree to the following:
              </Label>
            </div>
            
            <ul className="list-disc list-outside text-sm text-muted-foreground space-y-1 pl-8">
                <li>I meet the age requirements <i className="text-muted-foreground">(13+ or with guardian consent if under 18)</i></li>
                <li>I read and agree to the <span className="font-bold">Privacy Policy</span></li>
                <li>I read and agree to the <span className="font-bold">Terms of Use</span></li>
                <li>I read and understand the <span className="font-bold">Disclaimer</span></li>
            </ul>
        </div>


        <Accordion type="single" collapsible className="w-full">
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

        <DialogFooter className="sm:justify-center mt-2">
          <Button type="button" className="w-full" disabled={!agreed} onClick={onConsent}>
            Start Chatting Now
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
