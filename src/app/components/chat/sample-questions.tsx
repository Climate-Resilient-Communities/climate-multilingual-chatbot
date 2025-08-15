
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
    <div className="max-w-2xl mx-auto mb-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {questions.map((q) => (
                <Button
                    key={q}
                    variant="outline"
                    className="h-auto whitespace-normal text-left justify-start p-3 bg-primary/5 border-primary/20 hover:bg-primary/10 text-primary-dark"
                    onClick={() => onQuestionClick(q)}
                >
                    {q}
                </Button>
            ))}
        </div>
    </div>
  );
}
