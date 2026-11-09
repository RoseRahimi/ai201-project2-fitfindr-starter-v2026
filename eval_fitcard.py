#!/usr/bin/env python3
"""
Criterion 4: fit cards for five specific listings.

    python eval_fitcard.py --label before

criteria.md names five listing ids rather than queries, and no query reliably
selects a given listing, so this calls the tools directly instead of going
through run_agent. Each card gets a real outfit from suggest_outfit (example
wardrobe), the same way the loop does it. The cache is off and the temperature
is config.TEMPERATURE, as the criterion says.

Like run_eval.py, this records output and does not decide PASS or FAIL.
"""

import argparse
import datetime as dt

import config
import generate
from tools import suggest_outfit, create_fit_card
from utils.data_loader import load_listings, get_example_wardrobe

LISTING_IDS = ["lst_001", "lst_002", "lst_012", "lst_024", "lst_035"]


def main():
    parser = argparse.ArgumentParser(description="Generate criterion 4 fit cards.")
    parser.add_argument("--label", default="", help="a name for this run, e.g. 'before'")
    args = parser.parse_args()

    config.CACHE_ENABLED = False
    print("Cache is OFF for this run, on purpose.\n")

    by_id = {listing["id"]: listing for listing in load_listings()}
    wardrobe = get_example_wardrobe()

    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"fitcard_{stamp}{label}.md"

    lines = [
        f"# Criterion 4 fit cards{f' ({args.label})' if args.label else ''}",
        "",
        "- Produced by: `eval_fitcard.py::main`",
        "- Tools: `tools.py::suggest_outfit`, `tools.py::create_fit_card`",
        f"- Temperature: {config.TEMPERATURE}, caching off",
        f"- When: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "| Try | id | price | platform | brand | Pass? |",
        "|---|---|---|---|---|---|",
    ]
    for i, lid in enumerate(LISTING_IDS, 1):
        item = by_id[lid]
        lines.append(f"| {i} | {lid} | {item['price']} | {item['platform']} | {item['brand']} |  |")
    lines += ["", "---", ""]

    for i, lid in enumerate(LISTING_IDS, 1):
        item = by_id[lid]
        print(f"try {i}: {lid} {item['title']}")
        try:
            outfit = suggest_outfit(item, wardrobe)
            card = create_fit_card(outfit, item)
        except generate.ModelUnavailable as exc:
            outfit, card = "", f"(model unavailable: {exc})"
        lines += [
            f"### Try {i}: {lid}, {item['title']}",
            "",
            f"- price {item['price']}, platform {item['platform']}, brand {item['brand']}",
            "",
            "Fit card:", "", "```", card, "```", "",
            "Outfit it was given:", "", "```", outfit, "```", "",
        ]

    config.RESULTS_DIR.mkdir(exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {path.relative_to(config.ROOT)}")
    print(generate.usage())


if __name__ == "__main__":
    main()
