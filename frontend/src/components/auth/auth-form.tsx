"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth-provider";

const MIN_PASSWORD_LENGTH = 8;

// Only allow redirects to paths inside this app
function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";
}

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { status, login, register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = safeNext(searchParams.get("next"));
  const sessionExpired = searchParams.get("reason") === "expired";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isRegister = mode === "register";

  // Already signed in (e.g. session restored from the cookie)
  useEffect(() => {
    if (status === "authenticated") router.replace(next);
  }, [status, next, router]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (isRegister && password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters`);
      return;
    }
    setSubmitting(true);
    try {
      await (isRegister ? register(email, password) : login(email, password));
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setSubmitting(false);
    }
  };

  const otherHref = `${isRegister ? "/login" : "/register"}${
    next !== "/dashboard" ? `?next=${encodeURIComponent(next)}` : ""
  }`;

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-3 text-center">
          <Link
            href="/"
            className="mx-auto flex h-11 w-11 items-center justify-center rounded-lg bg-primary"
          >
            <Wallet className="h-6 w-6 text-primary-foreground" aria-hidden="true" />
            <span className="sr-only">Wallet Agent home</span>
          </Link>
          <CardTitle className="text-2xl">
            {isRegister ? "Create your account" : "Welcome back"}
          </CardTitle>
          <CardDescription>
            {isRegister
              ? "Start tracking your expenses in seconds"
              : "Sign in to your Wallet Agent account"}
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit} noValidate>
          <CardContent className="space-y-4">
            {sessionExpired && !error && (
              <p className="rounded-md bg-muted p-3 text-sm text-muted-foreground" role="status">
                Your session expired. Please sign in again.
              </p>
            )}
            {error && (
              <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete={isRegister ? "new-password" : "current-password"}
                required
                minLength={isRegister ? MIN_PASSWORD_LENGTH : undefined}
                aria-describedby={isRegister ? "password-hint" : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {isRegister && (
                <p id="password-hint" className="text-xs text-muted-foreground">
                  At least {MIN_PASSWORD_LENGTH} characters
                </p>
              )}
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-4">
            <Button type="submit" className="w-full" disabled={submitting || !email || !password}>
              {submitting
                ? isRegister
                  ? "Creating account..."
                  : "Signing in..."
                : isRegister
                  ? "Create account"
                  : "Sign in"}
            </Button>
            <p className="text-sm text-muted-foreground">
              {isRegister ? "Already have an account? " : "Don't have an account? "}
              <Link
                href={otherHref}
                className="font-medium text-primary underline-offset-4 hover:underline"
              >
                {isRegister ? "Sign in" : "Create one"}
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
