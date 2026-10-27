import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import {
  Wallet,
  PieChart,
  Bell,
  ArrowRight,
  Check,
  TrendingUp,
  Target,
  Sparkles,
  ArrowDownCircle,
} from "lucide-react";

const REPO_URL = "https://github.com/mahamudul-hasan-cse/Expense-tracker";

const features = [
  {
    icon: PieChart,
    title: "See where it goes",
    description: "Spending by category and by day, weekly or monthly, in Taka.",
  },
  {
    icon: TrendingUp,
    title: "Monthly budgets",
    description: "A limit per category, with a warning before you go over.",
  },
  {
    icon: ArrowDownCircle,
    title: "Income and savings rate",
    description: "Log salary and other income; see what you saved each month.",
  },
  {
    icon: Target,
    title: "Savings goals",
    description: "Set aside money for a laptop or a trip and see what to save each month.",
  },
  {
    icon: Bell,
    title: "Bills and reminders",
    description: "Recurring bills and income, with one tap to mark them paid.",
  },
  {
    icon: Sparkles,
    title: "AI assistant (optional)",
    description: "Ask in English or বাংলা, or type “rickshaw 80” to log an expense.",
  },
];

const benefits = ["Free and open source", "Works on your phone", "Dark mode", "CSV export"];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between gap-2 px-4">
          <Link href="/" className="flex items-center gap-2 sm:gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary shadow-lg shadow-primary/25">
              <Wallet className="h-5 w-5 text-primary-foreground" aria-hidden />
            </span>
            <span className="text-lg font-bold sm:text-xl">Wallet Agent</span>
          </Link>
          <nav aria-label="Account" className="flex items-center gap-1 sm:gap-2">
            <ThemeToggle />
            <Button asChild variant="ghost" size="sm">
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild size="sm" className="hidden shadow-lg shadow-primary/25 sm:inline-flex">
              <Link href="/register">Create account</Link>
            </Button>
          </nav>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))]" />
          <div className="container mx-auto px-4 pb-10 pt-12 text-center md:pb-16 md:pt-24">
            <div className="mx-auto max-w-3xl space-y-5 md:space-y-6">
              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
                Know where your{" "}
                <span className="bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
                  Taka
                </span>{" "}
                goes
              </h1>
              <p className="mx-auto max-w-2xl text-base text-muted-foreground sm:text-lg md:text-xl">
                Track expenses and income, set monthly budgets and savings goals, and get reminded
                about bills. Made for Bangladesh, in Taka.
              </p>
              <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Button
                  size="lg"
                  asChild
                  className="w-full gap-2 shadow-lg shadow-primary/25 sm:w-auto"
                >
                  <Link href="/register">
                    Create a free account
                    <ArrowRight className="h-4 w-4" aria-hidden />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" asChild className="w-full sm:w-auto">
                  <a href="#features">See what it does</a>
                </Button>
              </div>
              <ul className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 pt-2 text-sm text-muted-foreground">
                {benefits.map((benefit) => (
                  <li key={benefit} className="flex items-center gap-1.5">
                    <Check className="h-4 w-4 text-primary" aria-hidden />
                    {benefit}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* The real dashboard (seeded demo data) */}
        <section className="container mx-auto px-4 pb-12 md:pb-20">
          <div className="mx-auto max-w-5xl overflow-hidden rounded-xl border bg-card shadow-2xl shadow-primary/10 md:rounded-2xl">
            <Image
              src="/preview-dashboard.webp"
              alt="The Wallet Agent dashboard: total spent, daily average, bills due, this month's income and savings rate, and spending charts"
              width={1200}
              height={743}
              priority
              className="h-auto w-full dark:hidden"
            />
            <Image
              src="/preview-dashboard-dark.webp"
              alt="The Wallet Agent dashboard in dark mode"
              width={1200}
              height={743}
              priority
              className="hidden h-auto w-full dark:block"
            />
          </div>
        </section>

        {/* Features: icon beside the text keeps this short on phones */}
        <section id="features" className="scroll-mt-16 border-t bg-muted/30 py-12 md:py-20">
          <div className="container mx-auto px-4">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-2xl font-bold tracking-tight sm:text-4xl">
                Everything in one place
              </h2>
              <p className="mt-3 text-muted-foreground sm:text-lg">
                Simple tools to understand your money and keep more of it.
              </p>
            </div>
            <ul className="mx-auto mt-8 grid max-w-5xl gap-3 sm:grid-cols-2 md:mt-12 md:gap-6 lg:grid-cols-3">
              {features.map((feature) => (
                <li
                  key={feature.title}
                  className="flex gap-4 rounded-xl border bg-background/60 p-4 md:flex-col md:p-6"
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 md:h-12 md:w-12 md:rounded-xl">
                    <feature.icon className="h-5 w-5 text-primary md:h-6 md:w-6" aria-hidden />
                  </span>
                  <div>
                    <h3 className="font-semibold">{feature.title}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">{feature.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Call to action */}
        <section className="py-12 md:py-20">
          <div className="container mx-auto max-w-2xl space-y-5 px-4 text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-4xl">Start tracking today</h2>
            <p className="text-muted-foreground sm:text-lg">
              Create an account with your email. Your data is yours: export it any time.
            </p>
            <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Button
                size="lg"
                asChild
                className="w-full gap-2 shadow-lg shadow-primary/25 sm:w-auto"
              >
                <Link href="/register">
                  Create a free account
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
              </Button>
              <Button size="lg" variant="ghost" asChild className="w-full sm:w-auto">
                <Link href="/login">I already have an account</Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t bg-muted/30 py-6">
        <div className="container mx-auto flex flex-col items-center justify-between gap-3 px-4 text-sm text-muted-foreground sm:flex-row">
          <p>© 2026 Wallet Agent · MIT License</p>
          <a href={REPO_URL} className="transition-colors hover:text-foreground">
            Source code on GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
