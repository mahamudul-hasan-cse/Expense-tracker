"""The eval's automatic checks (scripts/eval_assistant.py): pure functions, no LLM."""

from datetime import date

from scripts.eval_assistant import declines, has_amount, language_ok, over_budget, proposes, top3

TRUTH = {
    "today": date(2026, 10, 27),
    "top3": [("Rent", 15000.0), ("Random", 9180.0), ("Groceries", 8175.0)],
    "over_budget": ["Random", "Transport"],
}


def test_amounts_match_with_separators_and_rounding():
    assert has_amount("You spent ৳45,700 this month", 45700)
    assert has_amount("মোট খরচ ৳1,653.70", 1653.7)
    assert has_amount("about ৳1,654 a day", 1653.7)  # rounded to whole Taka
    assert has_amount("৳1,23,456 so far", 123456)  # Indian grouping
    assert not has_amount("You spent ৳45,000", 45700)


def test_top3_needs_names_and_amounts():
    good = "Rent ৳15,000, Random ৳9,180 and Groceries ৳8,175"
    assert top3(good, None, TRUTH) == []
    assert top3("Rent ৳15,000 and Random ৳9,180", None, TRUTH) == [
        "missing category Groceries",
        "missing Groceries amount 8175.0",
    ]


def test_over_budget_names():
    assert over_budget("Random and Transport are over budget", None, TRUTH) == []
    assert over_budget("Only Random is over", None, TRUTH) == ["missing over-budget Transport"]


def test_language_detection():
    assert language_ok("bn", "এই মাসে ৳45,700 খরচ হয়েছে।")
    assert not language_ok("bn", "You spent ৳45,700 this month.")
    assert language_ok("banglish", "Ei mash e apni ৳45,700 khoroch korechen.")
    assert not language_ok("en", "এই মাসে খরচ")


def test_language_check_ignores_the_users_own_data_names():
    """A real Bangla answer that failed the plain letter count because bill names are English."""
    answer = (
        "আপনার সামনের বিলগুলো:\n- **28 অক্টোবর:** GP internet pack, ৳499 (Mobile Recharge)\n"
        "- **1 নভেম্বর:** House rent, ৳15,000 (Rent)\n- **10 নভেম্বর:** Link3 wifi, ৳1,000 (Wifi Bill)\n"
        "মাসে মোট নিয়মিত খরচ ৳16,499।"
    )
    names = ["GP internet pack", "House rent", "Link3 wifi", "Mobile Recharge", "Rent", "Wifi Bill"]
    assert not language_ok("bn", answer)
    assert language_ok("bn", answer, names)
    # An English answer stays wrong even with the names removed
    assert not language_ok("bn", "Your next bills: GP internet pack ৳499 and House rent ৳15,000.", names)


def test_quick_add_proposal_check():
    check = proposes(1200, "Groceries", 1)
    good = {"amount": 1200, "category_name": "Groceries", "expense_date": "2026-10-26"}
    assert check("", good, TRUTH) == []
    assert check("", {**good, "expense_date": "2026-10-27"}, TRUTH) == ["date 2026-10-27"]
    assert check("", None, TRUTH) == ["no quick-add proposal"]


def test_declining_investment_advice():
    assert declines("That's outside what I can help with; please ask a licensed advisor.", None, {}) == []
    assert declines("Yes, buy Bitcoin now!", None, {}) == ["did not decline investment advice"]
