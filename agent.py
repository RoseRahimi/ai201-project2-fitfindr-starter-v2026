"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import suggest_outfit, create_fit_card
from mcp_client import call_tool, MCPError
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── query parsing ─────────────────────────────────────────────────────────────
# Regex, no model call: parsing stays free, fast, and the same every run.

# "under $30", "below 30", "less than $25.50", "max $40", "up to $20", or a bare "$30"
_PRICE = re.compile(
    r"(?:under|below|less than|max|up to|<=?)\s*\$?\s*(\d+(?:\.\d+)?)|\$\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# only after the word "size", so the "s" at the end of "tees" is never read as a size
_SIZE = re.compile(
    r"\bsize\s+(us\s*\d+(?:\.\d+)?|w\d+(?:\s*l\d+)?|one size|extra large|"
    r"xxs|xs|xxl|xl|small|medium|large|s|m|l|\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)

_SIZE_WORDS = {"small": "S", "medium": "M", "large": "L", "extra large": "XL"}

# shopping filler the general stopword list in tools.py doesn't cover
_FILLER = {"looking", "want", "wanna", "need", "find", "something", "please", "im", "i'm", "size"}


def _parse_query(query: str) -> dict:
    """pull max_price and size out of the query; whatever is left is the description"""
    text = query or ""

    max_price = None
    price_match = _PRICE.search(text)
    if price_match:
        max_price = float(price_match.group(1) or price_match.group(2))
        text = text[:price_match.start()] + " " + text[price_match.end():]

    size = None
    size_match = _SIZE.search(text)
    if size_match:
        raw = size_match.group(1).strip()
        if raw.lower() in _SIZE_WORDS:
            size = _SIZE_WORDS[raw.lower()]
        elif re.fullmatch(r"\d+(?:\.\d+)?", raw):
            size = f"US {raw}"            # a bare number is a shoe size in this data
        else:
            size = raw.upper()
        text = text[:size_match.start()] + " " + text[size_match.end():]

    words = re.findall(r"[A-Za-z0-9'-]+", text)
    description = " ".join(w for w in words if w.lower() not in _FILLER)

    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """say what the user could change, based on which filters were actually applied"""
    asked = f"'{parsed['description']}'" if parsed["description"] else "your search"
    if parsed["size"]:
        asked += f" in size {parsed['size']}"
    if parsed["max_price"] is not None:
        asked += f" under ${parsed['max_price']:.2f}"

    fixes = []
    if parsed["max_price"] is not None:
        fixes.append(f"raise your price limit above ${parsed['max_price']:.0f}")
    if parsed["size"]:
        fixes.append("try a different size or leave the size out")
    fixes.append("use broader keywords (for example 'jacket' or 'tee' instead of a specific style)")

    return f"No listings matched {asked}. To find something, " + ", or ".join(fixes) + "."


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # Each pass runs one step, writes its result into the session, and picks the
    # next step from what that result was. Every tool reads its inputs back out
    # of the session rather than from a local variable.
    next_step = "parse"
    count = 0

    while next_step != "done":
        count += 1
        trace.check_iterations(count)

        if next_step == "parse":
            session["parsed"] = _parse_query(session["query"])
            trace.step("parse_query", inputs=session["query"], returned=str(session["parsed"]))
            next_step = "search"

        elif next_step == "search":
            parsed = session["parsed"]
            args = {
                "description": parsed["description"],
                "size": parsed["size"],
                "max_price": parsed["max_price"],
            }
            # search_listings now runs on the MCP server (mcp_server.py), not in-process
            try:
                session["search_results"] = call_tool("search_listings", args)
            except MCPError as exc:
                session["error"] = f"The search service couldn't be reached, so nothing was searched. {exc}"
                trace.step("search_listings (via MCP)", inputs=str(args), note="MCP call failed, stopping")
                next_step = "done"
                continue
            # THE BRANCH: nothing found means stop here, before any model call
            if not session["search_results"]:
                session["error"] = _no_results_message(session["parsed"])
                trace.step("search_listings (via MCP)", inputs=str(args),
                           returned=session["search_results"], note="branch: empty, stopping")
                next_step = "done"
            else:
                trace.step("search_listings (via MCP)", inputs=str(args),
                           returned=session["search_results"], note="branch: results, continuing")
                next_step = "select"

        elif next_step == "select":
            session["selected_item"] = session["search_results"][0]
            trace.step("select_item", returned=session["selected_item"],
                       note=f"id {session['selected_item']['id']}")
            next_step = "suggest"

        elif next_step == "suggest":
            item = session["selected_item"]
            try:
                session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])
            except ModelUnavailable as exc:
                session["error"] = f"Found {item.get('title')}, but couldn't write an outfit: {exc}"
                trace.step("suggest_outfit", inputs=f"item_id={item['id']}", note="model unavailable, stopping")
                next_step = "done"
                continue
            trace.step(
                "suggest_outfit",
                inputs=f"item_id={item['id']}, "
                       f"wardrobe_items={len((session['wardrobe'] or {}).get('items') or [])}",
                returned=session["outfit_suggestion"],
            )
            next_step = "fit_card"

        elif next_step == "fit_card":
            item = session["selected_item"]
            try:
                session["fit_card"] = create_fit_card(session["outfit_suggestion"], item)
            except ModelUnavailable as exc:
                session["error"] = f"Found {item.get('title')} and an outfit, but couldn't write the fit card: {exc}"
                trace.step("create_fit_card", inputs=f"item_id={item['id']}", note="model unavailable, stopping")
                next_step = "done"
                continue
            trace.step("create_fit_card", inputs=f"item_id={item['id']}", returned=session["fit_card"])
            next_step = "done"

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
