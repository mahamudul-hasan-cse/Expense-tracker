import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthForm } from "./auth-form";

const login = vi.fn();
const register = vi.fn();
const replace = vi.fn();
let searchParams = new URLSearchParams();

vi.mock("@/lib/auth-provider", () => ({
  useAuth: () => ({ status: "unauthenticated", login, register }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => searchParams,
}));

beforeEach(() => {
  vi.clearAllMocks();
  searchParams = new URLSearchParams();
});

async function fill(email: string, password: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Password"), password);
  return user;
}

describe("AuthForm", () => {
  it("register rejects short passwords before calling the API", async () => {
    render(<AuthForm mode="register" />);
    const user = await fill("a@example.com", "short");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(screen.getByRole("alert")).toHaveTextContent("at least 8 characters");
    expect(register).not.toHaveBeenCalled();
  });

  it("register signs up and goes to the dashboard", async () => {
    register.mockResolvedValue(undefined);
    render(<AuthForm mode="register" />);
    const user = await fill("a@example.com", "long-enough");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(register).toHaveBeenCalledWith("a@example.com", "long-enough");
    expect(replace).toHaveBeenCalledWith("/dashboard");
  });

  it("login shows the server error and lets the user retry", async () => {
    login.mockRejectedValue(new Error("Invalid email or password"));
    render(<AuthForm mode="login" />);
    const user = await fill("a@example.com", "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
    await waitFor(() => expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled());
    expect(replace).not.toHaveBeenCalled();
  });

  it("returns to the page the user came from", async () => {
    searchParams = new URLSearchParams({ next: "/expenses?page=2" });
    login.mockResolvedValue(undefined);
    render(<AuthForm mode="login" />);
    const user = await fill("a@example.com", "pw");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(replace).toHaveBeenCalledWith("/expenses?page=2");
  });

  it.each(["//evil.example.com", "https://evil.example.com", "javascript:alert(1)"])(
    "ignores unsafe next=%s (open redirect)",
    async (next) => {
      searchParams = new URLSearchParams({ next });
      login.mockResolvedValue(undefined);
      render(<AuthForm mode="login" />);
      const user = await fill("a@example.com", "pw");
      await user.click(screen.getByRole("button", { name: "Sign in" }));
      expect(replace).toHaveBeenCalledWith("/dashboard");
    }
  );

  it("shows the session-expired notice", () => {
    searchParams = new URLSearchParams({ reason: "expired" });
    render(<AuthForm mode="login" />);
    expect(screen.getByRole("status")).toHaveTextContent("Your session expired");
  });
});
