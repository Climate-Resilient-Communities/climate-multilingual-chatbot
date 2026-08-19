
"use client";

import { CloudSun, Droplets, Leaf, ThermometerSun } from "lucide-react";

type SampleQuestionsProps = {
    onQuestionClick: (question: string) => void;
};

const questions = [
    { icon: CloudSun, text: "What are the local impacts of climate change in Toronto?" },
    { icon: ThermometerSun, text: "Why is summer so hot now in Toronto?" },
    { icon: Droplets, text: "What can I do about flooding in Toronto?" },
    { icon: Leaf, text: "How to reduce my carbon footprint?" },
];

export function SampleQuestions({ onQuestionClick }: SampleQuestionsProps) {
  return (
    <div className="mx-auto w-full max-w-2xl">
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {questions.map(({ icon: Icon, text }) => (
                <button
                    key={text}
                    type="button"
                    className="group flex items-center gap-2.5 rounded-xl border bg-card/80 px-3.5 py-2.5 text-left text-[13px] text-foreground shadow-sm transition-colors hover:border-primary/40 hover:bg-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onClick={() => onQuestionClick(text)}
                >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary/15">
                        <Icon className="h-4 w-4" />
                    </span>
                    <span className="leading-snug">{text}</span>
                </button>
            ))}
        </div>
    </div>
  );
}
