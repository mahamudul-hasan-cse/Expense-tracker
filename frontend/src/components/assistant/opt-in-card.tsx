"use client";

import { Loader2, ShieldCheck, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** Shown until the user turns the assistant on. It's off by default. */
export function OptInCard({
  dailyLimit,
  onEnable,
  pending,
}: {
  dailyLimit: number;
  onEnable: () => void;
  pending: boolean;
}) {
  return (
    <Card className="mx-auto max-w-xl">
      <CardHeader>
        <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10">
          <Sparkles className="h-5 w-5 text-primary" />
        </div>
        <CardTitle>Meet your money assistant</CardTitle>
        <CardDescription>
          Ask about your spending in English or বাংলা, get saving tips based on your own numbers,
          and log expenses by just typing them.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <ul className="space-y-2">
          <li className="flex gap-2">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <span>
              To answer, it reads the parts of your expenses, income, budgets and goals that your
              question needs, and sends them to an AI provider (through OpenRouter). Only providers
              that keep nothing and never train on your data are used.
            </span>
          </li>
          <li className="flex gap-2">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <span>
              It can&apos;t change anything. New expenses are saved only when you confirm.
            </span>
          </li>
          <li className="flex gap-2">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <span>
              {dailyLimit} messages a day. You can delete your chats or turn it off at any time.
            </span>
          </li>
        </ul>
        <p className="text-muted-foreground">
          AI answers can be wrong; check important numbers on your dashboard. No investment, tax or
          legal advice.
        </p>
        <Button onClick={onEnable} disabled={pending} className="w-full sm:w-auto">
          {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Turn on assistant
        </Button>
      </CardContent>
    </Card>
  );
}
