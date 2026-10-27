"use client";

import Link from "next/link";
import { ArrowRight, RotateCcw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAssistantStatus, useWeeklyInsight } from "@/lib/queries";
import { Markdown } from "./markdown";

/**
 * AI-written summary of the week on the dashboard. Only for users who turned the
 * assistant on; the server writes it at most once a day and caches it.
 */
export function InsightCard() {
  const status = useAssistantStatus();
  const on = !!status.data?.configured && !!status.data?.enabled;
  const insight = useWeeklyInsight(on);
  if (!on) return null;

  return (
    <Card aria-label="This week's insight" role="region">
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Sparkles className="h-5 w-5 text-primary" />
          This week
        </CardTitle>
        <Link
          href="/assistant"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          Ask a follow-up
          <ArrowRight className="h-4 w-4" />
        </Link>
      </CardHeader>
      <CardContent className="text-sm">
        {insight.isLoading ? (
          <div className="space-y-2" aria-label="Writing this week's insight">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        ) : insight.isError ? (
          <div className="flex flex-wrap items-center gap-2 text-muted-foreground">
            <span>{insight.error.message || "Couldn't write this week's insight."}</span>
            <Button variant="outline" size="sm" className="h-8" onClick={() => insight.refetch()}>
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              Try again
            </Button>
          </div>
        ) : (
          insight.data && <Markdown text={insight.data.content} />
        )}
        <p className="mt-3 text-xs text-muted-foreground">
          Written by AI from your data. Check important numbers.
        </p>
      </CardContent>
    </Card>
  );
}
