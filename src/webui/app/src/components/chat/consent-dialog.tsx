
"use client";

import { useState } from "react";
import Image from "next/image";
import Logo from "@/app/Logo.png";
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
import { Separator } from "@/components/ui/separator";

type ConsentDialogProps = {
  open: boolean;
  onConsent: () => void;
};

export function ConsentDialog({ open, onConsent }: ConsentDialogProps) {
  const [agreed, setAgreed] = useState(false);

  return (
    <Dialog open={open}>
      <DialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-lg" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader className="space-y-2">
            <div className="flex justify-center">
                <Image src={Logo} alt="Logo" width={48} height={48} className="w-12 h-12" />
            </div>
          <DialogTitle className="text-center text-xl font-bold text-primary !mt-2">MLCC Climate Chatbot</DialogTitle>
          <DialogDescription className="text-center text-muted-foreground !mt-1">
            Connecting Toronto Communities to Climate Knowledge
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex justify-center py-2">
            <Separator className="w-1/2" />
        </div>
        
        <div className="space-y-3 text-xs">
            <p className="text-center text-muted-foreground">
              Welcome! This app shares clear info on climate impacts and local action. Please confirm you're good with the basics below.
            </p>

            <div className="flex items-start space-x-3 pt-2">
              <Checkbox id="terms" checked={agreed} onCheckedChange={(checked) => setAgreed(checked as boolean)} className="mt-0.5" />
              <div className="grid gap-1.5">
                <Label htmlFor="terms" className="font-medium leading-none text-foreground">
                    By checking this box, you agree to the following:
                </Label>
              </div>
            </div>
             <ul className="list-disc list-outside text-muted-foreground space-y-1 pl-8">
                <li>I meet the age requirements <i className="text-muted-foreground">(13+ or with guardian consent if under 18)</i></li>
                <li>I read and agree to the <span className="font-bold">Privacy Policy</span></li>
                <li>I read and agree to the <span className="font-bold">Terms of Use</span></li>
                <li>I read and understand the <span className="font-bold">Disclaimer</span></li>
            </ul>
        </div>


        <Accordion type="single" collapsible className="w-full text-xs">
          <AccordionItem value="privacy">
            <AccordionTrigger className="text-xs">Privacy Policy</AccordionTrigger>
            <AccordionContent className="max-h-48 overflow-y-auto pr-4">
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
            <AccordionContent className="max-h-48 overflow-y-auto pr-4">
              <div className="text-xs text-muted-foreground space-y-3">
                <p><strong>Terms of Use</strong><br />Last Updated: January 28, 2025</p>

                <div className="space-y-1">
                  <h4 className="font-semibold text-foreground">Acceptance of Terms</h4>
                  <p>By accessing and using the Climate Resilience Communities chatbot, you accept and agree to be bound by these Terms of Use and all applicable laws and regulations.</p>
                </div>

                <div className="space-y-1">
                  <h4 className="font-semibold text-foreground">Acceptable Use</h4>
                  <p>Users agree to use the chatbot in accordance with these terms and all applicable laws. Prohibited activities include but are not limited to:</p>
                  <ul className="list-disc list-outside space-y-1 pl-5">
                    <li>Spreading misinformation or deliberately providing false information</li>
                    <li>Engaging in hate speech or discriminatory behavior</li>
                    <li>Attempting to override or manipulate the chatbot's safety features</li>
                    <li>Using the service for harassment or harmful purposes</li>
                    <li>Attempting to extract personal information or private data</li>
                  </ul>
                </div>

                <div className="space-y-1">
                  <h4 className="font-semibold text-foreground">Open-Source License</h4>
                  <p>Our chatbot's codebase is available under the MIT License. This means you can:</p>
                  <ul className="list-disc list-outside space-y-1 pl-5">
                    <li>Use the code for any purpose</li>
                    <li>Modify and distribute the code</li>
                    <li>Use it commercially</li>
                    <li>Sublicense it</li>
                  </ul>
                  <p>Under the condition that:</p>
                   <ul className="list-disc list-outside space-y-1 pl-5">
                    <li>The original copyright notice and permission notice must be included</li>
                    <li>The software is provided "as is" without warranty</li>
                  </ul>
                </div>

                <div className="space-y-1">
                  <h4 className="font-semibold text-foreground">Intellectual Property</h4>
                  <p>While our code is open-source, the following remains the property of Climate Resilience Communities:</p>
                  <ul className="list-disc list-outside space-y-1 pl-5">
                    <li>Trademarks and branding</li>
                    <li>Content created specifically for the chatbot</li>
                    <li>Documentation and supporting materials</li>
                  </ul>
                </div>
                
                <div className="space-y-1">
                  <h4 className="font-semibold text-foreground">Liability Limitation</h4>
                  <p>The chatbot and its services are provided "as is" and "as available" without any warranties, expressed or implied. Climate Resilience Communities is not liable for any damages arising from:</p>
                  <ul className="list-disc list-outside space-y-1 pl-5">
                    <li>Use or inability to use the service</li>
                    <li>Reliance on information provided</li>
                    <li>Decisions made based on chatbot interactions</li>
                    <li>Technical issues or service interruptions</li>
                  </ul>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="disclaimer">
            <AccordionTrigger className="text-xs">Disclaimer</AccordionTrigger>
            <AccordionContent className="max-h-48 overflow-y-auto pr-4">
                <div className="text-xs text-muted-foreground space-y-3">
                    <p><strong>Disclaimer</strong><br />Last Updated: January 28, 2025</p>

                    <div className="space-y-1">
                        <h4 className="font-semibold text-foreground">General Information</h4>
                        <p>Climate Resilience Communities ("we," "our," or "us") provides this climate information chatbot as a public service to Toronto's communities. While we strive for accuracy and reliability, please note the following important limitations and disclaimers.</p>
                    </div>

                    <div className="space-y-1">
                        <h4 className="font-semibold text-foreground">Scope of Information</h4>
                        <p>The information provided through our chatbot is for general informational and educational purposes only. It does not constitute professional, legal, or scientific advice. Users should consult qualified experts and official channels for decisions regarding climate adaptation, mitigation, or response strategies.</p>
                    </div>

                    <div className="space-y-1">
                        <h4 className="font-semibold text-foreground">Information Accuracy</h4>
                        <p>While our chatbot uses Retrieval-Augmented Generation technology and cites verified sources, the field of climate science and related policies continues to evolve. We encourage users to:</p>
                        <ul className="list-disc list-outside space-y-1 pl-5">
                            <li>Verify time-sensitive information through official government channels</li>
                            <li>Cross-reference critical information with current scientific publications</li>
                            <li>Consult local authorities for community-specific guidance</li>
                        </ul>
                    </div>
                    
                    <div className="space-y-1">
                        <h4 className="font-semibold text-foreground">Third-Party Content</h4>
                        <p>Citations and references to third-party content are provided for transparency and verification. Climate Resilience Communities does not endorse and is not responsible for the accuracy, completeness, or reliability of third-party information.</p>
                    </div>
                </div>
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
