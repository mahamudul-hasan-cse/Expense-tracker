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

## Recommendation
- **Model:** `anthropic/claude-haiku-5.5`: best accuracy (18/18), fastest, and second-cheapest. It's already the built-in default.
- **Fallback:** `google/gemini-3.5-flash-lite` (18/18). It's a different vendor, so it covers an Anthropic outage.
  - Luna is cheaper but scored lower and renamed categories.
  - Sonnet is ~19× the cost with no accuracy gain here.
- Config: `ASSISTANT_MODEL=anthropic/claude-haiku-5.5` and `ASSISTANT_FALLBACK_MODELS=google/gemini-3.5-flash-lite`. **Not set yet: waiting for your decision.**

## Cost per message and limits
- **Haiku, average $0.00056 per message**. The range was $0.0002 (simple question) to $0.0014 (comparison with 3 rounds).
- The weekly insight costs ~$0.0013 per user per day, and only for users who turn the assistant on and open the dashboard.
- If every message fell back to Gemini, the average would be ~$0.0017.

**Recommended limits:**
- **Keep 20 messages per user per day.**
  - Typical cost: 20 × $0.00056 ≈ $0.011 per user per day.
  - Worst case (all heavy comparisons): ≈ $0.03.
- **Keep the global budget at $1/day for launch.**
  - That covers ~1,800 Haiku messages a day (about 90 users at the full cap), or ~600 if everything fell back to Gemini.
  - It caps the bill at ~$30/month.
  - Raise it to $2–3/day only if real usage regularly passes ~70% of the budget (check with `uv run python -m app.cli assistant-usage --days 7`).
- Also set a **monthly credit limit on the production OpenRouter key** (e.g. $10) as a hard stop that doesn't depend on our code.

## Spend
| Step | Cost |
|---|---|
| Eval round 1 (4 models × 18 + low subset) | $0.389 |
| Eval round 2 (4 models × 18) | $0.237 |
| Eval smoke test + insight check | $0.004 |
| **Key total so far (all assistant work, from OpenRouter's counter)** | **$0.688 of $2** (remaining $1.312) |

Full answers for both rounds are in the JSON files written by `--json` (not committed, since they contain demo data only and are large). Re-run with:

```bash
cd backend && uv run python -m scripts.seed_demo --reset
uv run python -m scripts.eval_assistant --models anthropic/claude-haiku-5.5,google/gemini-3.5-flash-lite --json eval.json
```
