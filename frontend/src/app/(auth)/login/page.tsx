import { Suspense } from "react";
import type { Metadata } from "next";
import { AuthForm } from "@/components/auth/auth-form";

export const metadata: Metadata = {
  title: "Sign in",
};

export default function LoginPage() {
  // AuthForm reads search params, which needs a Suspense boundary for static rendering
  return (
    <Suspense>
      <AuthForm mode="login" />
    </Suspense>
  );
}
