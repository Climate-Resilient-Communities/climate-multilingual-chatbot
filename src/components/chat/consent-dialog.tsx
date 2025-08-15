
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
import { Separator } from "@/components/ui/separator";

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
        
        <Separator className="w-1/2 mx-auto my-2" />

        <div className="space-y-4 my-2">
            <p className="text-xs text-center text-muted-foreground">
              Welcome! This app shares clear info on climate impacts and local action. Please confirm you're good with the basics below.
            </p>

            <div className="flex items-start space-x-3">
              <Checkbox id="terms" checked={agreed} onCheckedChange={(checked) => setAgreed(checked as boolean)} className="mt-1" />
              <div className="grid gap-2">
                <Label htmlFor="terms" className="text-xs font-medium leading-none text-foreground">
                    By checking this box, you agree to the following:
                </Label>
                <ul className="list-disc list-outside text-xs text-muted-foreground space-y-1 pl-5">
                    <li>I meet the age requirements <i className="text-muted-foreground">(13+ or with guardian consent if under 18)</i></li>
                    <li>I read and agree to the <span className="font-bold">Privacy Policy</span></li>
                    <li>I read and agree to the <span className="font-bold">Terms of Use</span></li>
                    <li>I read and understand the <span className="font-bold">Disclaimer</span></li>
                </ul>
              </div>
            </div>
        </div>


        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="privacy">
            <AccordionTrigger className="text-xs">Privacy Policy</AccordionTrigger>
            <AccordionContent>
              <div className="text-xs text-muted-foreground space-y-3">
                <p><strong>Privacy Policy</strong><br />Last Updated: January 28, 2025</p>

                <div className="space-y-1">
                  <h4 className="font-semibold text-foreground">Information Collection</h4>
                  <p>We are committed to protecting user privacy and minimizing data collection. Our practices include:</p>
                </div>

                <div className="space-y-1 pl-4">
                    <h5 className="font-semibold text-foreground">What We Do Not Collect</h5>
                    <ul className="list-disc list-outside space-y-1 pl-5">
                        <li>Personal identifying information (PII)</li>
                        <li>User accounts or profiles</li>
                        <li>Location data</li>
                        <li>Device information</li>
                        <li>Usage patterns</li>
                    </ul>
                </div>
                
                <div className="space-y-1 pl-4">
                    <h5 className="font-semibold text-foreground">What We Do Collect</h5>
                    <ul className="list-disc list-outside space-y-1 pl-5">
                        <li>Anonymized questions (with all PII automatically redacted)</li>
                        <li>Aggregate usage statistics</li>
                        <li>Error reports and system performance data</li>
                    </ul>
                </div>

                <div className="space-y-1">
                    <h4 className="font-semibold text-foreground">Data Usage</h4>
                    <p>Collected data is used exclusively for:</p>
                    <ul className="list-disc list-outside space-y-1 pl-5">
                        <li>Improving chatbot response accuracy</li>
                        <li>Identifying common climate information needs</li>
                        <li>Enhancing language processing capabilities</li>
                        <li>System performance optimization</li>
                    </ul>
                </div>

                <div className="space-y-1">
                    <h4 className="font-semibold text-foreground">Data Protection</h4>
                    <p>We protect user privacy through:</p>
                    <ul className="list-disc list-outside space-y-1 pl-5">
                        <li>Automatic PII redaction before caching</li>
                        <li>Secure data storage practices</li>
                        <li>Limited access controls</li>
                    </ul>
                </div>
                
                <div className="space-y-1">
                    <h4 className="font-semibold text-foreground">Third-Party Services</h4>
                    <p>Our chatbot utilizes Cohere's language models. Users should note:</p>
                    <ul className="list-disc list-outside space-y-1 pl-5">
                        <li>No personal data is shared with Cohere</li>
                        <li>Questions are processed without identifying information</li>
                        <li>Cohere's privacy policies apply to their services</li>
                    </ul>
                </div>

                <div className="space-y-1">
                    <h4 className="font-semibold text-foreground">Changes to Privacy Policy</h4>
                    <p>We reserve the right to update this privacy policy as needed. Users will be notified of significant changes through our website.</p>
                </div>

                <div className="space-y-1">
                    <h4 className="font-semibold text-foreground">Contact Information</h4>
                    <p>For privacy-related questions or concerns, contact us at info@crcgreen.com</p>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="terms">
            <AccordionTrigger className="text-xs">Terms of Use</AccordionTrigger>
            <AccordionContent>
              <p className="text-xs text-muted-foreground">
                This service is provided under the MIT License. You are free to use it for any purpose, but the authors and copyright holders are not liable for any claims, damages, or other liability. Use the information provided at your own risk.
              </p>
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="disclaimer">
            <AccordionTrigger className="text-xs">Disclaimer</AccordionTrigger>
            <AccordionContent>
              <p className="text-xs text-muted-foreground">
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
