# Assistant: real example conversations (Phase A1)

Run 2026-10-26 with the **real OpenRouter API**: model `anthropic/claude-haiku-5.5` (the documented default, not yet approved as final), ZDR-only routing, `data_collection: deny`. The data is the seeded demo user (`backend/scripts/seed_demo.py`, Jul 27 – Oct 26, 2026).

Reproduce with:
```
cd backend && uv run python -m scripts.try_assistant "<message>"
```
Tool results are shortened here; the model received the full JSON.

---

## 1. English: month-over-month comparison and saving advice

**User:** How did my spending this month compare with last month, and where can I save money?

**Tool calls** (chosen by the model, run on the server with the signed-in user's id):
1. `compare_periods({"period_a": {"start_date": "2026-09-01", "end_date": "2026-09-30"}, "period_b": {"start_date": "2026-10-01", "end_date": "2026-10-26"}})` → Sep ৳41,715 (90 expenses), Oct so far ৳45,700 (72), change +৳3,985 (+9.6%), biggest change Random ৳985 → ৳9,180
2. `get_budgets_status({"month": "2026-10"})` → Random 306% (projected ৳10,945.38), Transport 128.2%, Groceries 90.8% at risk, …
3. `detect_unusual_spending({"start_date": "2026-10-01", "end_date": "2026-10-26"})` → Random at 14.4× its usual daily rate; ৳8,500 "Eid shopping, Bashundhara City" on Oct 14

**Assistant:**
> **Short answer:** Spending is up ৳3,985 (9.6%) so far this month, and almost all of the increase comes from one category, "Random." October also has only 26 days so far, compared with September's full 30.
>
> **Month-over-month (Sep 1–30 vs Oct 1–26)**
> - September: ৳41,715 across 90 expenses
> - October so far: ৳45,700 across 72 expenses
>
> **What changed by category**
> - **Random:** ৳985 → ৳9,180 (+৳8,195). This is the main driver. A single ৳8,500 entry on Oct 14 ("Eid shopping, Bashundhara City") accounts for most of it. Your usual Random spending is far lower; the tool puts it at about 14 times your normal daily rate.
> - **Groceries:** ৳9,315 → ৳8,175 (−12.2%)
> - **Food:** ৳5,845 → ৳4,845 (−17.1%)
> - **Transport:** ৳3,670 → ৳3,205 (−12.7%)
> - **Health:** ৳1,750 → ৳560 (−68%)
> - **Mobile Recharge:** ৳600 → ৳800 (+33.3%)
>
> **Budgets this month**
> - **Random:** ৳9,180 spent against a ৳3,000 limit (306%). Projected month-end: ৳10,945. Over budget.
> - **Transport:** ৳3,205 against ৳2,500 (128%). Projected: ৳3,821. Over budget.
> - **Groceries:** ৳8,175 against ৳9,000 (91%). Projected: ৳9,747. At risk.
> - **Food:** ৳4,845 against ৳7,000 (69%). On track.
> - **Rickshaw:** ৳1,035 against ৳1,800 (58%). On track.
>
> **Where you can save**
> 1. **Plan for one-off big purchases.** Eid shopping isn't a recurring habit, but it hit a category with a small budget. Consider a separate "festival" budget or a savings goal for Eid, Pohela Boishakh and similar occasions, so it doesn't push Random far over.
> 2. **Bring Transport back under ৳2,500.** It's already ৳705 over with about five days left. Check whether a few rides could be walked, shared, or swapped for a cheaper route.
> 3. **Watch Groceries for the rest of the month.** It has only ৳825 left and is projected to end at ৳9,747, so slow down on non-essential grocery trips.
>
> If you want, I can look at your savings goals or upcoming recurring bills to see how these overruns affect them.

*2 LLM requests · 8,133 prompt tokens · 1,464 output tokens (331 reasoning) · 10.8 s · **$0.001702***

---

## 2. Bangla: budget status and top categories

**User:** এই মাসে আমার বাজেটের অবস্থা কেমন? কোন খাতে বেশি খরচ হচ্ছে?

**Tool calls:**
1. `get_budgets_status({})` → (current month by default) the same budget figures as above
2. `get_spending_summary({"start_date": "2026-10-01", "end_date": "2026-10-26", "group_by": "category"})` → total ৳45,700; Rent ৳15,000 (32.8%), Random ৳9,180 (20.1%), Groceries ৳8,175 (17.9%), …

**Assistant:**
> এই মাসের (১–২৬ অক্টোবর) বাজেটের অবস্থা ভালো নয়। দুটি খাত ইতিমধ্যে বাজেট ছাড়িয়ে গেছে, আর একটি ঝুঁকিতে আছে।
>
> **বাজেটের অবস্থা**
>
> - **Random (🎲):** বাজেট ৳3,000, খরচ ৳9,180 (306%)। বাজেট ৳6,180 ছাড়িয়েছে। মাস শেষে আনুমানিক ৳10,945 দাঁড়াতে পারে। 🔴
> - **Transport (🚕):** বাজেট ৳2,500, খরচ ৳3,205 (128%)। বাজেট ৳705 ছাড়িয়েছে। মাস শেষে আনুমানিক ৳3,821। 🔴
> - **Groceries (🛒):** বাজেট ৳9,000, খরচ ৳8,175 (91%)। বাকি আছে ৳825। মাস শেষে আনুমানিক ৳9,747, অর্থাৎ বাজেট ছাড়িয়ে যাওয়ার ঝুঁকি আছে। 🟠
> - **Food (🍛):** বাজেট ৳7,000, খরচ ৳4,845 (69%)। বাকি ৳2,155। ঠিক আছে। 🟢
> - **Rickshaw (🛺):** বাজেট ৳1,800, খরচ ৳1,035 (58%)। বাকি ৳765। ঠিক আছে। 🟢
>
> **সবচেয়ে বেশি খরচ হচ্ছে যেখানে**
>
> মোট খরচ ৳45,700। এর মধ্যে:
> 1. **Rent (🏠):** ৳15,000 (33%)। এটি একটিমাত্র খরচ, এবং বর্তমানে কোনো বাজেট সেট করা নেই।
> 2. **Random (🎲):** ৳9,180 (20%), ১৪টি খরচ।
> 3. **Groceries (🛒):** ৳8,175 (18%), ৪টি খরচ।
> 4. **Food (🍛):** ৳4,845 (11%), ১৮টি খরচ।
> 5. **Transport (🚕):** ৳3,205 (7%), ৭টি খরচ।
>
> **পরামর্শ**
>
> - **Random খাতটি সবচেয়ে জরুরি।** আমি চাইলে এই খাতের ১৪টি খরচের তালিকা দেখাতে পারি, যাতে বোঝা যায় কোথায় বেশি গেছে। এর মধ্যে কিছু কমানো সম্ভব কিনা দেখুন।
> - **Transport-এর জন্য** বাকি মাসে যাতায়াতের খরচ সীমিত রাখুন। Rickshaw খাত ঠিক চলছে, তাই যাতায়াতের বড় অংশ সম্ভবত অন্য Transport খরচ থেকে আসছে।
> - **Groceries-এর বাকি ৳825** ধরে খরচ করুন। সপ্তাহে একবার বাজার করলে সুবিধা হবে।
> - **Rent বাজেটে যোগ করুন।** তাহলে মাসিক খরচের পুরো ছবি পাবেন।
>
> চাইলে Random-এর খরচের বিস্তারিত তালিকা দেখতে পারি।

*2 LLM requests · 7,858 prompt tokens (6,254 from cache) · 1,625 output tokens (291 reasoning) · 9.2 s · **$0.001035***

---

## 3. Quick add (Bangla, Bangla digits)

**User:** আজ দুপুরের খাবার ২৫০ টাকা

**Tool calls:**
1. `list_categories({})` → the user's 11 expense categories (Food 🍛, Groceries 🛒, Rickshaw 🛺, …) and income categories
2. `propose_expense({"amount": 250, "category": "Food", "expense_date": "2026-10-26", "note": "দুপুরের খাবার"})` → `{"proposal": {"amount": 250.0, "category_name": "Food", "category_icon": "🍛", "expense_date": "2026-10-26", "note": "দুপুরের খাবার", …}, "status": "proposed, NOT saved"}`

**Streamed `proposal` event:** shown in the UI (Phase A3) as a confirmation card with Confirm / Edit / Cancel.

**Assistant:**
> দুপুরের খাবারের জন্য ৳২৫০ (Food, আজ ২৬ অক্টোবর) প্রস্তুত করেছি। কার্ডটি দেখে নিশ্চিত করুন (Confirm) — তারপরই এটি সেভ হবে।

**Checked afterwards:** the demo user still had **267 expenses** (nothing saved), and the stored message carries the proposal with status `pending`.

*3 LLM requests · 10,860 prompt tokens (9,381 from cache) · 294 output tokens · 5.0 s · **$0.000389***

---

## Spend
| What | Cost |
|---|---|
| These 3 conversations | $0.003126 |
| Development runs (first attempts, finish-reason/reasoning diagnosis, 3 streaming checks) | $0.010420 |
| **Total real API spend so far** | **$0.013546 of $2.00** (OpenRouter `/key`, matches the app's `assistant-usage` report plus one $0.00017 diagnostic call made outside the app) |

The average cost per message so far is about $0.001 for the cheap model. Final per-message figures and limits come with the 4-model eval (Phase A4).
