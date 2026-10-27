import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AssistantMessage, ExpenseProposal } from "@/types";
import { ProposalCard } from "./proposal-card";

const confirmProposal = vi.fn();
const cancelProposal = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: {
    confirmProposal: (...a: unknown[]) => confirmProposal(...a),
    cancelProposal: (...a: unknown[]) => cancelProposal(...a),
  },
}));

const proposal: ExpenseProposal = {
  amount: 1250.5,
  category_id: "c1",
  category_name: "Food",
  category_icon: "🍔",
  expense_date: "2026-10-27",
  note: "দুপুরের খাবার",
};

function reply(status: AssistantMessage["proposal_status"]): AssistantMessage {
  return {
    id: "m1",
    role: "assistant",
    content: "",
    proposal,
    proposal_status: status,
    expense_id: status === "confirmed" ? "e1" : null,
    status: "ok",
    created_at: "2026-10-27T06:00:00Z",
  };
}

function renderCard(props: Partial<React.ComponentProps<typeof ProposalCard>> = {}) {
  const onChange = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ProposalCard
        proposal={proposal}
        status="pending"
        messageId="m1"
        onChange={onChange}
        {...props}
      />
    </QueryClientProvider>
  );
  return { onChange, user: userEvent.setup() };
}

beforeEach(() => vi.clearAllMocks());

describe("ProposalCard", () => {
  it("shows amount and date with English digits, even for a Bangla note", () => {
    renderCard();
    const card = screen.getByRole("region", { name: "Expense to confirm" });
    expect(card).toHaveTextContent("৳1,250.5");
    expect(card).toHaveTextContent("Oct 27, 2026");
    expect(card.textContent).not.toMatch(/[০-৯]/);
  });

  it("sends one confirm request even when Save is double-clicked", async () => {
    let resolve: (m: AssistantMessage) => void = () => {};
    confirmProposal.mockReturnValue(new Promise((r) => (resolve = r)));
    const { onChange, user } = renderCard();
    const save = screen.getByRole("button", { name: /Save expense/ });
    await user.dblClick(save);
    expect(save).toBeDisabled();
    resolve(reply("confirmed"));
    await vi.waitFor(() => expect(onChange).toHaveBeenCalledWith(reply("confirmed")));
    expect(confirmProposal).toHaveBeenCalledTimes(1);
    expect(confirmProposal).toHaveBeenCalledWith("m1");
  });

  it("can't be saved while the answer is still streaming", () => {
    renderCard({ messageId: null });
    expect(screen.getByRole("button", { name: /Save expense/ })).toBeDisabled();
  });

  it.each([
    ["confirmed", "Saved to your expenses"],
    ["cancelled", "Not saved"],
    ["expired", "Expired after 24 hours"],
  ] as const)("shows the %s state without action buttons", (status, text) => {
    renderCard({ status });
    expect(screen.getByRole("status")).toHaveTextContent(text);
    expect(screen.queryByRole("button", { name: /Save expense/ })).toBeNull();
  });

  it("shows the server's reason when saving fails", async () => {
    const { ApiError } = await import("@/lib/api");
    confirmProposal.mockRejectedValue(new ApiError("Proposal expired; ask again to log it", 409));
    const { user } = renderCard();
    await user.click(screen.getByRole("button", { name: /Save expense/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Proposal expired");
  });
});
