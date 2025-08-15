
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
                    className="h-auto whitespace-normal text-left justify-start p-3 bg-card text-sm font-normal text-card-foreground border-border hover:bg-accent hover:shadow-sm transition-transform duration-200 ease-in-out hover:-translate-y-1"
                    onClick={() => onQuestionClick(q)}
                >
                    {q}
                </Button>
            ))}
        </div>
    </div>
  );
}
