import { Fragment, ReactNode } from "react";

/**
 * Renders the small Markdown subset the assistant uses: paragraphs, "-"/"*" and
 * "1." lists, "#" headings, **bold**, *italic* / _italic_ and `code`.
 * Builds React elements only (never raw HTML), so model output can't inject markup.
 * Works on partial text while an answer is still streaming.
 */
export function Markdown({ text }: { text: string }) {
  return <div className="space-y-2 break-words leading-relaxed">{renderBlocks(text)}</div>;
}

type Block =
  | { kind: "p"; lines: string[] }
  | { kind: "ul" | "ol"; items: string[] }
  | { kind: "h"; text: string };

const BULLET = /^\s*[-*•]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;

export function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  for (const line of text.split("\n")) {
    const last = blocks[blocks.length - 1];
    let m: RegExpMatchArray | null;
    if (!line.trim()) {
      blocks.push({ kind: "p", lines: [] }); // paragraph break
    } else if ((m = line.match(HEADING))) {
      blocks.push({ kind: "h", text: m[1] });
    } else if ((m = line.match(BULLET)) || (m = line.match(NUMBERED))) {
      const kind = BULLET.test(line) ? "ul" : "ol";
      if (last?.kind === kind) last.items.push(m[1]);
      else blocks.push({ kind, items: [m[1]] });
    } else if (last?.kind === "p") {
      last.lines.push(line);
    } else if ((last?.kind === "ul" || last?.kind === "ol") && /^\s{2,}/.test(line)) {
      last.items[last.items.length - 1] += " " + line.trim(); // wrapped list item
    } else {
      blocks.push({ kind: "p", lines: [line] });
    }
  }
  return blocks.filter((b) => b.kind !== "p" || b.lines.length > 0);
}

function renderBlocks(text: string): ReactNode[] {
  return parseBlocks(text).map((block, i) => {
    switch (block.kind) {
      case "h":
        return (
          <p key={i} className="font-semibold">
            {renderInline(block.text)}
          </p>
        );
      case "ul":
      case "ol": {
        const List = block.kind;
        return (
          <List
            key={i}
            className={`space-y-1 pl-5 ${block.kind === "ul" ? "list-disc" : "list-decimal"}`}
          >
            {block.items.map((item, j) => (
              <li key={j}>{renderInline(item)}</li>
            ))}
          </List>
        );
      }
      default:
        return (
          <p key={i}>
            {block.lines.map((line, j) => (
              <Fragment key={j}>
                {j > 0 && <br />}
                {renderInline(line)}
              </Fragment>
            ))}
          </p>
        );
    }
  });
}

// **bold**, `code`, *italic* or _italic_ (underscores only at word edges, so snake_case stays)
const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*|(?<![\w])_[^_\s][^_]*_(?![\w]))/g;

export function renderInline(text: string): ReactNode[] {
  return text.split(INLINE).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4)
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2)
      return (
        <code key={i} className="rounded bg-muted px-1 py-0.5 text-[0.9em]">
          {part.slice(1, -1)}
        </code>
      );
    if (
      part.length > 2 &&
      ((part.startsWith("*") && part.endsWith("*")) || (part.startsWith("_") && part.endsWith("_")))
    )
      return <em key={i}>{part.slice(1, -1)}</em>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}
