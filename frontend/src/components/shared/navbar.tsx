"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  ArrowDownCircle,
  LayoutDashboard,
  List,
  LogOut,
  Settings,
  Target,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-provider";
import { ThemeToggle } from "./theme-toggle";

const LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/expenses", label: "Expenses", icon: List },
  { href: "/income", label: "Income", icon: ArrowDownCircle },
  { href: "/goals", label: "Goals", icon: Target },
  { href: "/settings", label: "Settings", icon: Settings },
];

/**
 * Top bar with the logo, page links (md and up), theme and sign-out. On phones the
 * page links move to a bottom tab bar with labels (MobileNav).
 */
export function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // RequireAuth sends the now signed-out user to /login
  const handleLogout = () => logout().catch(() => undefined);

  return (
    <>
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4">
          <div className="flex h-16 items-center justify-between gap-4">
            <Link href="/dashboard" className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary shadow-lg shadow-primary/25">
                <Wallet className="h-5 w-5 text-primary-foreground" aria-hidden />
              </span>
              <span className="text-xl font-bold">Wallet Agent</span>
            </Link>
            <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
              {LINKS.map((link) => {
                const Icon = link.icon;
                const isActive = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    aria-current={isActive ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all lg:px-4",
                      isActive
                        ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                    {/* Icon-only between md and lg so five links fit; the name stays for screen readers */}
                    <span className="sr-only lg:not-sr-only">{link.label}</span>
                  </Link>
                );
              })}
            </nav>
            <div className="flex items-center gap-1 md:border-l md:pl-2">
              <ThemeToggle />
              <Button
                variant="ghost"
                size="icon"
                className="h-9 w-9"
                onClick={handleLogout}
                aria-label={user ? `Sign out ${user.email}` : "Sign out"}
                title={user ? `Sign out (${user.email})` : "Sign out"}
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>
      <MobileNav pathname={pathname} />
    </>
  );
}

/** Bottom tab bar on phones: every page reachable with one tap, with a visible label. */
function MobileNav({ pathname }: { pathname: string }) {
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-50 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur supports-[backdrop-filter]:bg-background/80 md:hidden"
    >
      <ul className="grid grid-cols-5">
        {LINKS.map((link) => {
          const Icon = link.icon;
          const isActive = pathname === link.href;
          return (
            <li key={link.href}>
              <Link
                href={link.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-medium",
                  isActive ? "text-primary" : "text-muted-foreground"
                )}
              >
                <span
                  className={cn(
                    "flex h-7 w-12 items-center justify-center rounded-full",
                    isActive && "bg-primary/10"
                  )}
                >
                  <Icon className="h-5 w-5" aria-hidden />
                </span>
                {link.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
