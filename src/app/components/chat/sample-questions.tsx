
"use client";

import { Button } from "@/components/ui/button";

type SampleQuestionsProps = {
    onQuestionClick: (question: string) => void;
};

const questions = [
    "What are the local impacts of climate change in Toronto?",
    "Why is summer so hot now in Toronto?",
    "What can I do about flooding in Toronto?",
    "How to reduce my carbon footprint?",
];

export function SampleQuestions({ onQuestionClick }: SampleQuestionsProps) {
  return (
    <div className="max-w-2xl mx-auto mb-4 px-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {questions.map((q) => (
                <Button
                    key={q}
                    variant="outline"
                    className="h-auto whitespace-normal text-left justify-start p-3 text-xs font-normal bg-card/60 border-border/80 hover:bg-accent hover:border-accent-foreground/20"
                    onClick={() => onQuestionClick(q)}
                >
                    {q}
                </Button>
            ))}
        </div>
    </div>
  );
}
