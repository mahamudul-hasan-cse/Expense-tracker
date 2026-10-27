import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Markdown, parseBlocks } from "./markdown";

describe("Markdown", () => {
  it("renders lists, bold, italic and paragraphs", () => {
    const { container } = render(
      <Markdown
        text={
          "**Food** is your top category.\n\n- Food: ৳12,450 (38%)\n- Transport: ৳4,100\n\n1. Cook at home\n2. Walk short trips\n\n_Cut short_"
        }
      />
    );
    expect(container.querySelector("strong")?.textContent).toBe("Food");
    expect(container.querySelectorAll("ul li")).toHaveLength(2);
    expect(container.querySelectorAll("ol li")).toHaveLength(2);
    expect(container.querySelector("em")?.textContent).toBe("Cut short");
  });

  it("never renders model output as HTML", () => {
    const { container } = render(
      <Markdown text={'<img src=x onerror="alert(1)"> **<b>hi</b>**'} />
    );
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
    expect(container.textContent).toContain("<img src=x");
  });

  it("keeps snake_case words and lone asterisks as text", () => {
    const { container } = render(<Markdown text="use list_expenses for 5 * 3 items" />);
    expect(container.querySelector("em")).toBeNull();
    expect(container.textContent).toBe("use list_expenses for 5 * 3 items");
  });

  it("handles a half-streamed answer without crashing", () => {
    expect(parseBlocks("- Food: ৳12,4")).toEqual([{ kind: "ul", items: ["Food: ৳12,4"] }]);
    const { container } = render(<Markdown text="**Foo" />);
    expect(container.textContent).toBe("**Foo");
  });
});
