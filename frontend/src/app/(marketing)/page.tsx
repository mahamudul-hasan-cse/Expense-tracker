"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import {
  Wallet,
  PieChart,
  Bell,
  Download,
  Shield,
  Zap,
  ArrowRight,
  Check,
  TrendingUp,
  Calendar,
  Tag,
} from "lucide-react";

const features = [
  {
    icon: PieChart,
    title: "Visual Analytics",
    description:
      "Beautiful charts showing your spending patterns by category, weekly and monthly trends.",
  },
  {
    icon: Bell,
    title: "Recurring Reminders",
    description:
      "Never miss a bill. Set up recurring expenses and get timely reminders before they're due.",
  },
  {
    icon: Tag,
    title: "Smart Categories",
    description:
      "Organize expenses with custom categories and icons. Quick-add buttons for frequent spending.",
  },
  {
    icon: TrendingUp,
    title: "Budget Goals",
    description: "Set monthly budgets per category and track your progress with visual indicators.",
  },
  {
    icon: Calendar,
    title: "Date Filtering",
    description:
      "Filter expenses by date range, category, or search by notes to find any transaction.",
  },
  {
    icon: Download,
    title: "CSV Export",
    description: "Export your expense data anytime for taxes, reports, or backup purposes.",
  },
];

const benefits = [
  "Free to use",
  "No credit card required",
  "Dark mode support",
  "Mobile responsive",
  "Fast & lightweight",
  "Privacy focused",
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary shadow-lg shadow-primary/25">
              <Wallet className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">Wallet Agent</span>
          </Link>
          <div className="flex items-center gap-4">
            <ThemeToggle />
            <Button asChild className="shadow-lg shadow-primary/25">
              <Link href="/dashboard">
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))]" />
        <div className="container mx-auto px-4 py-20 text-center md:py-32">
          <div className="mx-auto max-w-3xl space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border bg-primary/5 px-4 py-1.5 text-sm text-primary">
              <Zap className="h-4 w-4" />
              <span>Simple expense tracking that works</span>
            </div>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
              Take Control of Your{" "}
              <span className="bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
                Spending
              </span>
            </h1>
            <p className="mx-auto max-w-2xl text-lg text-muted-foreground md:text-xl">
              A clean, fast expense tracker with beautiful charts, budget goals, and recurring
              reminders. No signup required — start tracking in seconds.
            </p>
            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button size="lg" asChild className="gap-2 shadow-lg shadow-primary/25">
                <Link href="/dashboard">
                  Start Tracking Free
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <a href="#features">See Features</a>
              </Button>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 pt-4 text-sm text-muted-foreground">
              {benefits.map((benefit) => (
                <div key={benefit} className="flex items-center gap-1.5">
                  <Check className="h-4 w-4 text-primary" />
                  <span>{benefit}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Dashboard Preview */}
      <section className="container mx-auto px-4 pb-20">
        <div className="mx-auto max-w-5xl overflow-hidden rounded-2xl border bg-card shadow-2xl shadow-primary/10">
          <div className="flex items-center gap-2 border-b bg-muted/50 px-4 py-3">
            <div className="h-3 w-3 rounded-full bg-rose-500" />
            <div className="h-3 w-3 rounded-full bg-amber-500" />
            <div className="h-3 w-3 rounded-full bg-emerald-500" />
            <span className="ml-4 text-sm text-muted-foreground">wallet-agent.app/dashboard</span>
          </div>
          <div className="aspect-video bg-gradient-to-br from-primary/5 via-transparent to-purple-500/5 p-8">
            <div className="grid h-full grid-cols-3 gap-4">
              {/* Mock Dashboard Cards */}
              <div className="space-y-4">
                <div className="rounded-xl bg-background p-4 shadow-sm">
                  <div className="text-sm text-muted-foreground">This Week</div>
                  <div className="text-2xl font-bold text-primary">$847.50</div>
                </div>
                <div className="rounded-xl bg-background p-4 shadow-sm">
                  <div className="text-sm text-muted-foreground">This Month</div>
                  <div className="text-2xl font-bold">$2,340.00</div>
                </div>
                <div className="space-y-2 rounded-xl bg-background p-4 shadow-sm">
                  <div className="text-sm font-medium">Quick Add</div>
                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-lg bg-primary/10 px-2 py-1 text-sm">🍔 Food</span>
                    <span className="rounded-lg bg-primary/10 px-2 py-1 text-sm">🚗 Transport</span>
                    <span className="rounded-lg bg-primary/10 px-2 py-1 text-sm">🛒 Shopping</span>
                  </div>
                </div>
              </div>
              {/* Mock Chart */}
              <div className="col-span-2 rounded-xl bg-background p-4 shadow-sm">
                <div className="mb-4 text-sm font-medium">Spending by Category</div>
                <div className="flex h-[80%] items-end justify-around gap-2">
                  {[65, 45, 80, 35, 55, 70, 40].map((height, i) => (
                    <div
                      key={i}
                      className="w-full rounded-t-lg bg-gradient-to-t from-primary to-purple-400"
                      style={{ height: `${height}%` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="border-t bg-muted/30 py-20">
        <div className="container mx-auto px-4">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Everything you need to manage expenses
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Simple tools that help you understand where your money goes and stay on budget.
            </p>
          </div>
          <div className="mx-auto mt-16 grid max-w-5xl gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <Card
                key={feature.title}
                className="group border bg-background/50 transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5"
              >
                <CardContent className="pt-6">
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 transition-colors group-hover:bg-primary/20">
                    <feature.icon className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="mb-2 font-semibold">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Start in 3 simple steps
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              No complicated setup. No account required. Just start tracking.
            </p>
          </div>
          <div className="mx-auto mt-16 grid max-w-4xl gap-8 md:grid-cols-3">
            {[
              {
                step: "1",
                title: "Add Categories",
                description:
                  "Set up your spending categories like Food, Transport, Entertainment with custom icons.",
              },
              {
                step: "2",
                title: "Log Expenses",
                description:
                  "Quickly add expenses with amount, category, and optional notes. Takes seconds.",
              },
              {
                step: "3",
                title: "Track Progress",
                description:
                  "View charts, set budgets, and understand your spending habits over time.",
              },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-xl font-bold text-primary-foreground shadow-lg shadow-primary/25">
                  {item.step}
                </div>
                <h3 className="mb-2 font-semibold">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative overflow-hidden border-t py-20">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_80%_50%_at_50%_100%,rgba(120,119,198,0.1),rgba(255,255,255,0))]" />
        <div className="container mx-auto px-4 text-center">
          <div className="mx-auto max-w-2xl space-y-6">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <Shield className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Ready to take control?
            </h2>
            <p className="text-lg text-muted-foreground">
              Join thousands who track their expenses with Wallet Agent. Free forever, no strings
              attached.
            </p>
            <Button size="lg" asChild className="gap-2 shadow-lg shadow-primary/25">
              <Link href="/dashboard">
                Start Tracking Now
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-muted/30 py-8">
        <div className="container mx-auto flex flex-col items-center justify-between gap-4 px-4 text-sm text-muted-foreground sm:flex-row">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Wallet className="h-4 w-4 text-primary-foreground" />
            </div>
            <span>© 2026 Wallet Agent. All rights reserved.</span>
          </div>
          <div className="flex gap-6">
            <a href="#" className="transition-colors hover:text-foreground">
              Privacy
            </a>
            <a href="#" className="transition-colors hover:text-foreground">
              Terms
            </a>
            <a href="#" className="transition-colors hover:text-foreground">
              Contact
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
