
"use client";

import { Button } from "@/components/ui/button";

type SampleQuestionsProps = {
    onQuestionClick: (question: string) => void;
};

const questions = [
    "How does flooding from the Don River affect Thorncliffe Park?",
    "What cooling resources exist near Thorncliffe Park during heat waves?",
    "How does air quality near the DVP impact Thorncliffe residents?",
    "What tree planting programs are available in Thorncliffe Park?",
];

export function SampleQuestions({ onQuestionClick }: SampleQuestionsProps) {
  return (
    <div className="max-w-4xl mx-auto w-full mt-8 px-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {questions.map((q) => (
                <Button
                    key={q}
                    variant="outline"
                    className="h-auto whitespace-normal justify-center p-3 text-xs font-normal bg-card/60 border-border/80 hover:bg-accent hover:border-accent-foreground/20 transition-transform hover:-translate-y-1 hover:text-primary"
                    onClick={() => onQuestionClick(q)}
                >
                    {q}
                </Button>
            ))}
        </div>
    </div>
  );
}
