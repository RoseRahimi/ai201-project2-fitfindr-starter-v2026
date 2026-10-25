# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**How it's checked:** run each of these once with `python app.py ask` (5 tries, one per query). A try passes if `session["error"]` is None and `session["fit_card"]` is a non-empty string.

1. `'vintage graphic tee under $30'`
2. `'baggy jeans'`
3. `'denim jacket size S'`
4. `'chunky cardigan'`
5. `'white sneakers under $50'`

Each of these returns at least one listing when called on `search_listings` directly, so a failure is in the loop or the model calls, not in the data.

**Why this target:** this path makes 2 model calls per run (`suggest_outfit` and `create_fit_card`) on a free tier capped at 15 requests per minute. A quota error, a network blip, or an empty model response can break one run even when my code is right, so I allow one miss. It is not 3 of 5 because search itself makes no model call and has no randomness, and the adapter already paces requests, so more than one miss means a real bug, most likely in how `run_agent` parses the query.

<!-- Why 4 of 5 and not 5 of 5? Something about your search, probably —
     "my search is a plain keyword match and some phrasings will miss" is a
     real answer. -->

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**How it's checked:** run each of these once with `python app.py ask` (5 tries, one per query). A try passes if `session["outfit_suggestion"]` and `session["fit_card"]` are both None, and `session["error"]` mentions at least one of: price, size, or keywords (case-insensitive).

1. `'designer ballgown size XXS under $5'`
2. `'leather bomber under $10'`
3. `'jeans size L'`
4. `'sweatshirt size S'`
5. `'wedding tuxedo'`

Each of these returns `[]` from `search_listings` directly.

**Why this target:** the branch runs before any model call, so it uses none of the 15 requests per minute and contains nothing random. Only the full matching path (2 model calls) can vary from run to run, so this branch should hold every time.

<!-- Why is 5 of 5 reasonable here when criterion 1 isn't? What's different
     about this path? -->

---

## 3. The selected item is the item the next tools receive

For each of the 5 queries from criterion 1, run through `python app.py ask`:

- the `id` in `session["selected_item"]` equals the `id` of the listing logged in the `suggest_outfit` trace step (the trace step has to log the item's `id`), and
- the fit card names no price or platform that differs from `selected_item`'s.

A price counts only when it is written as a dollar figure (`$38`, `$38.00`). Phrases like "under $40" or "cheap" are not prices. A platform counts when depop, poshmark or thredUp appears, case-insensitive. Target: 5 of 5.

<!-- YOU WRITE THIS ONE.

     How would you know that the item your search found is the same item the
     next tool received? Name something countable or observable.

     This is the criterion people find hardest, because state failure doesn't
     look like state failure — it looks like a tool problem. Something that
     compares session["selected_item"] against what actually reached
     suggest_outfit is the shape you're after. -->

**Why this target: every listing has a unique id (for example lst_001), so the comparison is an exact field match with no model randomness on the trace side. Passing the item along is plain code, so anything below 5 of 5 is a bug. The fit card half lets me spot it from output alone: a card quoting a price that is not the selected listing's means the wrong item was handed over. A card that leaves the price out does not fail this criterion; that is a model issue covered by criterion 4.**

---

## 4.  The fit card

Generate cards for these 5 listings with temperature 0.9 and the cache off:

| id | item | price | platform | brand |
| -- | ---- | ----- | -------- | ----- |
| lst_001 | Vintage Levi's 501 Jeans | 38.0 | depop | Levi's |
| lst_002 | Y2K Baby Tee | 18.0 | depop | None |
| lst_012 | Oversized Crewneck Sweatshirt | 20.0 | thredUp | None |
| lst_024 | Vintage Polo Shirt | 18.0 | thredUp | Ralph Lauren |
| lst_035 | Low-Top Canvas Sneakers | 20.0 | poshmark | None |

A card passes if all of these hold:

1. It is 2 to 4 sentences. A sentence ends in `.`, `!` or `?`. A line made only of hashtags or emoji doesn't count as a sentence.
2. It contains the listing's exact price: a dollar figure in the card, read as a float, equals the listing's `price` (`$38` and `$38.00` both equal 38.0).
3. It names the listing's platform, case-insensitive.
4. If brand is None, it contains none of these brand names: Champion, Demonia, Levi's, Ralph Lauren, Woolrich, Wrangler (every brand in the data), Nike, Adidas, Converse, Vans, Carhartt, Dickies, Patagonia, Zara, H&M, Gap, Dr. Martens.

Target: at least 4 of 5 cards pass, and 0 of 5 contain a wrong price or an invented brand.

<!-- YOU WRITE THIS ONE.

     The fit card calls a model, so the same input can produce different words
     each time. That's not a bug — it's the nature of the tool. So what would
     make it acceptable?

     Think about what you'd actually be unhappy to see. A caption that never
     mentions the price? Two different items producing the same opening
     sentence? A card longer than a caption anyone would post? Any of those can
     be turned into a number. -->

**Why this target:** at temperature 0.9 with the cache off the wording changes every run, so I only count what my prompt explicitly asks for and what can be checked by string match. Sentence count can drift at that temperature, so 4 of 5 is realistic. A wrong price or a made up brand when brand is None is the output I would be embarrassed to post, so that part has no allowance. Three of the five listings have no brand because 32 of the 40 listings in the data have none, so the brand check gets tested where it matters most.

---

## 5. Size Traps

Run these 5 queries through `python app.py ask`, so the query parsing in `run_agent` is part of the test:

1. `'tees size S'`
2. `'top size S'`
3. `'blazer size S'`
4. `'jacket size L'`
5. `'graphic tee size L'`

A try passes if `session["parsed"]` has the requested size, and every listing in `session["search_results"]` has the requested size as a whole token (`S` matches `S/M`) or is One Size. In particular, "S" never returns a US shoe size and "L" never returns a plain "XL". Each query returns at least one listing, so a pass can't come from an empty result. Target: 5 out of 5.

<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. Speed, the empty
     wardrobe path, what happens when the model can't be reached, whether the
     search respects a price ceiling — anything, as long as it names a number
     or an observable outcome. -->

**Why this target:** a substring check for "S" would match the S in "US 9", and "L" would match inside "XL". `search_listings` matches whole size tokens to avoid that, but the query parser in `run_agent` is the part that can still miss: it has to pull "S" out of `'tees size S'` without mistaking the "s" at the end of "tees" for a size. The whole path is deterministic, with no model call before search, so anything below 5 of 5 is a bug, which is why the target is 5 and not 4.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
