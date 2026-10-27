"use client";

import { useState } from "react";
import { Loader2, Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useAssistantStatus, useDeleteConversation, useSetAssistantEnabled } from "@/lib/queries";

/** Assistant opt-in, what data is shared, and deleting chat history. */
export function AssistantSettings() {
  const { toast } = useToast();
  const status = useAssistantStatus();
  const setEnabled = useSetAssistantEnabled();
  const deleteAll = useDeleteConversation();
  const [confirming, setConfirming] = useState(false);

  if (!status.data?.configured) return null; // nothing to set up without a server key
  const enabled = status.data.enabled;

  const toggle = () =>
    setEnabled.mutate(!enabled, {
      onSuccess: (s) =>
        toast({ title: s.enabled ? "Assistant turned on" : "Assistant turned off" }),
      onError: (e) => toast({ title: "Error", description: e.message, variant: "destructive" }),
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">AI Assistant</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-medium" id="assistant-toggle-label">
              Use the assistant
            </p>
            <p className="text-muted-foreground">
              {enabled ? "On" : "Off"} · {status.data.daily_limit} messages a day
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={enabled}
            aria-labelledby="assistant-toggle-label"
            onClick={toggle}
            disabled={setEnabled.isPending}
            className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 ${
              enabled ? "bg-primary" : "bg-input"
            }`}
          >
            <span
              className={`inline-block h-5 w-5 rounded-full bg-background shadow transition-transform ${
                enabled ? "translate-x-5" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>

        <p className="rounded-lg bg-muted/50 p-3 text-muted-foreground">
          Your questions, and the parts of your expenses, income, budgets and goals needed to answer
          them, are sent to OpenRouter and the AI model provider. Only providers that keep nothing
          and never train on your data are used. The assistant can&apos;t change your data; new
          expenses are saved only when you confirm them.
        </p>

        <Button
          variant="outline"
          className="gap-2 text-destructive hover:text-destructive"
          onClick={() => setConfirming(true)}
        >
          <Trash2 className="h-4 w-4" />
          Delete my chat history
        </Button>

        <AlertDialog open={confirming} onOpenChange={setConfirming}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete all assistant chats?</AlertDialogTitle>
              <AlertDialogDescription>
                This removes every conversation and the saved weekly insights. Expenses you saved
                from a chat are kept. This can&apos;t be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() =>
                  deleteAll.mutate(null, {
                    onSuccess: () => toast({ title: "Chat history deleted" }),
                    onError: (e) =>
                      toast({ title: "Error", description: e.message, variant: "destructive" }),
                  })
                }
              >
                {deleteAll.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Delete everything
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardContent>
    </Card>
  );
}
