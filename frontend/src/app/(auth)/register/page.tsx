import { Suspense } from "react";
import type { Metadata } from "next";
import { AuthForm } from "@/components/auth/auth-form";

export const metadata: Metadata = {
  title: "Create account · Wallet Agent",
};

export default function RegisterPage() {
  // AuthForm reads search params, which needs a Suspense boundary for static rendering
  return (
    <Suspense>
      <AuthForm mode="register" />
    </Suspense>
  );
}
