"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

# Criteria 1 and 3 are scored from the same runs: criterion 1 reads whether the
# run finished with a fit card, criterion 3 reads the trace and the card for the
# selected item's id, price and platform.
#
# Criterion 4 targets five specific listing ids rather than queries, so it is not
# here. It runs from eval_fitcard.py.

_CRITERION_1_AND_3 = [
    "vintage graphic tee under $30",
    "baggy jeans",
    "denim jacket size S",
    "chunky cardigan",
    "white sneakers under $50",
]

_CRITERION_2 = [
    "designer ballgown size XXS under $5",
    "leather bomber under $10",
    "jeans size L",
    "sweatshirt size S",
    "wedding tuxedo",
]

_CRITERION_5 = [
    "tees size S",
    "top size S",
    "blazer size S",
    "jacket size L",
    "graphic tee size L",
]

SCENARIOS = (
    [{"name": f"c1+3 completes: {q}", "query": q, "wardrobe": "example", "criterion": 1}
     for q in _CRITERION_1_AND_3]
    + [{"name": f"c2 stops early: {q}", "query": q, "wardrobe": "example", "criterion": 2}
       for q in _CRITERION_2]
    + [{"name": f"c5 size trap: {q}", "query": q, "wardrobe": "example", "criterion": 5}
       for q in _CRITERION_5]
    + [{
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    }]
)

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
