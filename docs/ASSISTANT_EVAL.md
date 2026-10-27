# Assistant model evaluation (Phase A4, 2026-10-27)

`backend/scripts/eval_assistant.py` runs 18 questions (7 English, 6 Bangla, 5 Banglish) for the seeded demo user (`scripts.seed_demo --reset`) through the real chat service and OpenRouter, with our privacy routing (ZDR, no data collection). Each answer is checked automatically against ground truth computed from the database (the same SQL the tools use):

- the key numbers appear (±1 Taka or ±0.5%), and the named categories, goals and bills are mentioned;
- quick adds propose the right amount, category and date;
- investment advice is declined;
- the reply is in the question's script (Bangla script for Bangla, Latin letters for English and Banglish).

The scoring functions have their own unit tests (`tests/test_eval_checks.py`). Times are measured from sending the message: first status line, first answer text, and the full answer. "Raw BN digits" counts Bangla answers where the model itself wrote ০-৯; the server converts these to 0-9, so users never see them.

## Round 1: prompt rule only

| Model | Reasoning | Accuracy | Right script | Raw BN digits | First status | First text | Total | LLM rounds | $/message |
|---|---|---|---|---|---|---|---|---|---|
| anthropic/claude-haiku-5.5 | default | 16/18 | 16/18 | 4/6 | 1.9s | 4.2s | 5.9s | 2.0 | $0.00057 |
| anthropic/claude-haiku-5.5 | low (6 q) | 6/6 | 6/6 | 0/3 | 1.8s | 5.8s | 6.6s | 2.2 | $0.00060 |
| openai/gpt-6-luna | default | 14/18 | 14/18 | 0/6 | 3.7s | 8.2s | 8.8s | 2.1 | $0.00043 |
| openai/gpt-6-luna | low (6 q) | 4/6 | 4/6 | 0/3 | 3.3s | 4.9s | 6.2s | 2.0 | $0.00041 |
| google/gemini-3.5-flash-lite | default | 13/18 | 13/18 | 1/6 | 3.8s | 8.3s | 9.0s | 1.9 | $0.00163 |
| google/gemini-3.5-flash-lite | low (6 q) | 5/6 | 5/6 | 1/3 | 3.7s | 8.0s | 8.6s | 2.2 | $0.00186 |
| anthropic/claude-sonnet-5.5 | default | 11/18 | 11/18 | 0/6 | 2.5s | 7.9s | 8.4s | 2.1 | $0.01448 |
| anthropic/claude-sonnet-5.5 | low (6 q) | 4/6 | 4/6 | 0/3 | 1.9s | 5.8s | 6.2s | 2.0 | $0.01074 |

**Finding: almost every failure was the wrong script, not wrong numbers.**
- Haiku, Luna and Gemini answered Banglish questions in Bangla script.
- Sonnet answered **all 7 English questions in Bangla**.

The system prompt's "match their script" rule wasn't enough. **Fix:** the server detects the script and adds an explicit note to each user turn: "reply in Bangla script" or "reply in Latin letters only". The note isn't stored and isn't shown to the user. There's a regression test.

## Round 2: with the per-turn script note (default reasoning)

| Model | Accuracy | Right script | Raw BN digits | First status | First text | Total | LLM rounds | $/message | Notes |
|---|---|---|---|---|---|---|---|---|---|
| **anthropic/claude-haiku-5.5** | **18/18** | 18/18 | 3/6 | 2.1s | **4.5s** | 6.4s | 2.1 | **$0.00056** | Fastest; every check passed |
| google/gemini-3.5-flash-lite | 18/18 | 18/18 | 3/6 | 3.5s | 6.7s | 7.3s | 1.9 | $0.00168 | All passed; ~2s slower, 3× Haiku's cost |
| anthropic/claude-sonnet-5.5 | 17/18 | 18/18 | 0/6 | 2.2s | 8.1s | 8.3s | 2.1 | $0.01049 | The one "miss" compared Oct 1–27 with Sep 1–27 (a fair like-for-like reading); 19× Haiku's cost |
| openai/gpt-6-luna | 16/18 | 17/18 | 0/6 | 3.3s | 7.1s | 7.9s | 2.0 | $0.00044 | 1 provider error ("unavailable"); translated category names in Bangla ("ভাড়া" for Rent), which no longer match the app |

Single runs: latency varies by about ±2s between runs, and one provider error is noise. Accuracy differences of 1–2 questions are within that noise; the script-error pattern in round 1 was consistent across models.

## Reasoning setting
- `low` didn't make Haiku faster: first text 5.8s with low vs 4.2s with default (round 1). It wasn't more accurate either.
- `none` (measured earlier) gets text out quickly, but answered Bangla questions in English.
- **Keep the default** (`ASSISTANT_REASONING_EFFORT` unset), as decided.

## Recommendation (first pass)
- **Model:** `anthropic/claude-haiku-5.5`: best accuracy (18/18), fastest, and second-cheapest.
- **Fallback:** `google/gemini-3.5-flash-lite` (18/18). It's a different vendor, so it covers an Anthropic outage.
  - Luna is cheaper but scored lower and renamed categories.
  - Sonnet is ~19× the cost with no accuracy gain here.

## Cheaper messages (2026-10-27, owner request)
Same 18 questions, Haiku 5.5, default reasoning. "Before" is the code as of round 2, re-measured the same day.

| | Before | After |
|---|---|---|
| Accuracy | 18/18 | **18/18** |
| Right script | 18/18 | **18/18** |
| **Cost per message** | **$0.00069** | **$0.00041** (−41%) |
| Cache-hit rate (share of prompt tokens read from cache) | 71% | **87%** |
| Prompt tokens per message | 8,383 | 8,695 |
| Output tokens per message (incl. reasoning) | 704 | 438 |
| Largest single request output | 1,014 | 802–1,137 |
| First text / total (avg) | 4.1s / 6.1s | 3.6s / 4.3s |

What changed, and what each part did (measured step by step, all at 18/18):
1. **Shorter answers.** Prompt: answer only what was asked; about 120 words or 6 bullets by default; only the relevant categories; at most 2 suggestions, only when asked; no closing offers; fetch only the tools the question needs. Output fell from 704 to 460 tokens per message.
2. **Compact tool results.** The same JSON without spaces after separators, so fewer uncached input tokens.
3. **Caching.** The tools and system prompt were already first and identical, with the date, category names and script note after them. The real leak was routing: Haiku is served by ~10 provider endpoints, each with its own cache. The sticky-routing key was per *conversation*, so every new chat started on a random endpoint with a cold cache. It's now one key per *user* (hashed). Cache hits went from 70% to 86–87%, and cost per message from $0.00060 to $0.00041–0.00044.
4. **Less history.** The last 6 messages (3 exchanges) instead of 20. Answers older than the latest are cut to their first 400 characters. Tool calls and results were never stored, so they're never resent. *The 18-question eval is single-turn, so it can't measure this; it only lowers cost in longer chats (unit-tested).*
5. **Max output tokens: 1,600 → 1,500.** One Bangla budget answer used 1,137 tokens in a single request (mostly hidden reasoning), and 800 once cut answers short, so the cap keeps ~30% headroom. The cap only limits the worst case; the savings come from step 1.

## Haiku 5.5 vs Qwen (same 18 questions, cheaper settings)
Qwen candidates were checked against our privacy routing (zero data retention + no data collection + tool support):

| Qwen model | Eligible? |
|---|---|
| qwen3.8-flash, qwen3.7-flash, qwen3.8-omni-flash, qwen3.6-flash, qwen3.7-plus, qwen3.6-plus, qwen3.5-plus, qwen3.8-max | ❌ no zero-data-retention endpoint |
| **qwen3.8-27b**, qwen3.6-35b-a3b, qwen3.6-27b | ✅ |

Picked **`qwen/qwen3.8-27b`**: the newest eligible model, and the cheapest in the probe.

| Model | Accuracy | Right script | Cost per message | Cache hit | First text | Total | Notes |
|---|---|---|---|---|---|---|---|
| **anthropic/claude-haiku-5.5** | **18/18** | **18/18** | **$0.00041** | 87% | 3.6s | 4.3s | |
| qwen/qwen3.8-27b | 16/18 | 17/18 | $0.00221 | 54% | 4.2s | 6.4s | One malformed tool call on the English comparison (error); a "yesterday" quick add dated today; one 5-round answer cost $0.009 |

**Rule:** choose Qwen only with 18/18 accuracy, 18/18 script and a lower cost per message. Qwen failed all three, so **Haiku 5.5 stays**. `ASSISTANT_MODEL=anthropic/claude-haiku-5.5` is now set explicitly in `config.py` and `.env.example`. The fallback is kept as it is: no fallback model is configured (`ASSISTANT_FALLBACK_MODELS` empty). Gemini 3.5 Flash Lite is still the recommended one if you want one.

## Cost per message and limits
- **Haiku, average $0.00041 per message** after the cost work. The range was $0.0001 (declining advice) to $0.0010 (comparison with 3 rounds).
- The weekly insight costs ~$0.0013 per user per day, only for users who turn the assistant on and open the dashboard.

**Limits:**
- **Per user: 50 messages per day** (raised from 20 on 2026-10-27; it works exactly as before, just a higher number).
  - Typical cost: 50 × $0.00041 ≈ $0.02 per user per day.
  - Worst case (all heavy comparisons): ≈ $0.05.
- **Global: $1/day** (unchanged). That covers ~2,400 Haiku messages a day (about 48 users at the full 50-message cap) and caps the bill at ~$30/month. Raise it only if real usage regularly passes ~70% of the budget (`uv run python -m app.cli assistant-usage --days 7`).
- Also set a **monthly credit limit on the production OpenRouter key** (e.g. $10) as a hard stop that doesn't depend on our code.

## Spend
| Step | Cost |
|---|---|
| Eval round 1 (4 models × 18 + low subset) | $0.389 |
| Eval round 2 (4 models × 18) | $0.237 |
| Eval smoke test + insight check | $0.004 |
| Cost work: 4 Haiku runs (before, 2 intermediate, after) + final Haiku run | $0.046 |
| Qwen: privacy-routing probes + 18-question eval | $0.041 |
| **Key total so far (all assistant work, from OpenRouter's counter)** | **$0.777 of $2** (remaining $1.223) |

Full answers for both rounds are in the JSON files written by `--json` (not committed, since they contain demo data only and are large). Re-run with:

```bash
cd backend && uv run python -m scripts.seed_demo --reset
uv run python -m scripts.eval_assistant --models anthropic/claude-haiku-5.5,google/gemini-3.5-flash-lite --json eval.json
```
