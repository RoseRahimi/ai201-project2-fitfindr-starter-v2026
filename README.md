# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr takes a plain-language thrift request like `'vintage graphic tee under $30'` or `'denim jacket size S'` and searches 40 secondhand listings from depop, poshmark and thredUp for the best match within that price and size. For the top match, it suggests one or two outfits that pair the item with specific pieces from the user's wardrobe (or with common basics if the wardrobe is empty), then writes a short social media caption about the find that mentions its price and platform. If nothing matches, it stops before calling the model and tells the user what to change: the price limit, the size, or the keywords.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters the 40 listings by price and size, then ranks what's left by how many keywords from the description appear in each listing (title, category, brand, style tags and colors count 2 points; the description text counts 1).
- **Inputs:** `description` (str), `size` (str or None, None skips the size filter), `max_price` (float or None, inclusive, None skips the price filter). A size matches on whole size tokens, case-insensitive: `"M"` matches `"S/M"` and `"M/L"`, but `"S"` does not match `"US 9"` and `"L"` does not match `"XL"`. Text in parentheses is ignored, so `"XL (oversized)"` counts as `XL`, and "One Size" listings match any size.
- **Returns:** A list of up to 10 listing dicts (`config.SEARCH_RESULT_LIMIT`), best match first. Each dict has `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None) and `platform`.
- **When it has nothing:** An empty list `[]`, never None and never an exception. This also happens when the description has no usable keywords.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the new item, using pieces from the user's wardrobe by name.
- **Inputs:** `new_item` (dict, one listing dict from `search_listings`), `wardrobe` (dict with an `items` key holding a list of wardrobe item dicts, each with `name`, `category`, `colors`, `style_tags` and optional `notes`).
- **Returns:** A non-empty string (under about 120 words) describing one or two outfits that name specific wardrobe pieces alongside the new item.
- **When it has nothing:** If the wardrobe is empty, it still returns a non-empty string of general styling advice built on common basics (plain tee, jeans, sneakers). If the model returns an empty response, it returns a short fallback sentence instead of `""`.

### `create_fit_card`

- **What it does:** Asks the model to write a short social media caption about the find, in the voice of a real post rather than a product listing.
- **Inputs:** `outfit` (str, the suggestion from `suggest_outfit`), `new_item` (dict, the selected listing dict).
- **Returns:** A 2 to 4 sentence caption string that mentions the item, its price and its platform once each and describes the vibe.
- **When it has nothing:** If `outfit` is empty or only whitespace, it returns the string `"No outfit suggestion to caption, so there's no fit card for this item."` without calling the model. If the model returns an empty response, it returns a one-line fallback caption with the item, price and platform.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that tells the user what to change (raise the price limit, try a different size, or use broader keywords) and stop without calling `suggest_outfit`. Otherwise, take the first result, store it in `session["selected_item"]`, and go to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** With regex in `agent.py::_parse_query`, no model call, so parsing is free and gives the same result every run. The price comes from phrases like "under $30", "below 30", "up to $20" or a bare "$30". The size is only read after the word "size" ("size S", "size US 9", "size small"), so the "s" at the end of "tees" is never mistaken for a size. "small", "medium" and "large" become S, M and L, and a bare number like "size 9" becomes "US 9" because only shoes have number sizes in this data. Whatever is left, minus filler words like "looking" and "want", is the description. The result goes into `session["parsed"]` as `{"description", "size", "max_price"}`.

**What moves through the session:** `run_agent` is a loop where each pass runs one step, writes its result into the session, and picks the next step from that result. Every tool reads its inputs back out of the session, never from the previous call's return value:

1. `parse` reads `session["query"]` and writes `session["parsed"]`.
2. `search` reads `session["parsed"]` and writes `session["search_results"]`. If that list is empty, it writes `session["error"]` and the loop ends.
3. `select` reads `session["search_results"][0]` and writes `session["selected_item"]`.
4. `suggest` reads `session["selected_item"]` and `session["wardrobe"]` and writes `session["outfit_suggestion"]`.
5. `fit_card` reads `session["outfit_suggestion"]` and `session["selected_item"]` and writes `session["fit_card"]`.

Each pass calls `trace.check_iterations(count)`, so a branch that never ends raises instead of looping forever.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop

  Outfit:   Hey! That 2003 tour tee is an awesome find—definitely worth grabbing for $24! It’ll fit right into your grunge-streetwear vibe. 

Here are two effortless ways to style it using what you already own:

**Outfit 1: Casual & Edgy**
Pair the Graphic Tee with your **Baggy straight-leg jeans, dark wash**. Add the **Black combat boots** and the **Black crossbody bag**. Throw your **Vintage black denim jacket** on top for that effortless, double-black denim texture.

**Outfit 2: High-Contrast Streetwear**
Tuck the Graphic Tee into your **Wide-leg khaki trousers** (cinched with the **Brown leather belt**). Layer the **Black cropped zip hoodie** unzipped over it, and finish the look with your **Chunky white sneakers** for a cool mix of vintage and modern street style.

  Fit card: scored this 2003 tour bootleg tee on depop for just $24 and it's honestly the ultimate grunge-streetwear staple. been living in it paired with baggy dark wash denim and combat boots for that effortless edgy look, but it also looks so good dressed down with khaki trousers and sneakers. total vintage score!

2 model calls this session, 592 prompt + 259 output tokens
```

And the branch, on a query that matches nothing:

```
$ python app.py ask 'designer ballgown size XXS under $5'

  No listings matched 'designer ballgown' in size XXS under $5.00. To find something, raise your price limit above $5, or try a different size or leave the size out, or use broader keywords (for example 'jacket' or 'tee' instead of a specific style).

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0, 'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Hey there! Grab those Vintage Levi's 501 Jeans—at $38, they are an absolute steal. Here are two effortless ways to style them using pieces you already own:

**Outfit 1: Casual & Cool**
Pair the Vintage Levi's 501 Jeans with your White ribbed tank top tucked in, layered under the Vintage black denim jacket. Finish with your Chunky white sneakers and the Black crossbody bag for an easy, classic weekend look. 

**Outfit 2: Streetwear Edge**
Cinch the Vintage Levi's 501 Jeans with your Brown leather belt, and pair them with the Oversized grey crewneck sweatshirt. Throw on your Black combat boots to lean into that effortless, slouchy streetwear vibe.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Nothing beats the fit of broken-in vintage denim, especially when you score them for just $38. Paired these thrifted Levi's 501s with my go-to white sneakers for that effortlessly cool 90s streetwear vibe. So glad I hunted these down on Depop before someone else did!
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I had started `search_listings` with a 9-word stopword list (`a`, `an`, `and`, `with`, `under`, `over`, `of`, `in`, `for`). I asked Claude to make it a complete stopword list, then asked why stopwords are needed at all.
- *What came back:* The full 179-word English list (the same words as NLTK's), and a test showing why it matters: without stopwords, `'a ballgown for the gala with a train'` returned 10 unrelated listings (a track jacket, cargo pants, a cardigan) only because their descriptions contain "a" and "the". With them, it returns `[]`.
- *What I changed:* I replaced my short list with the full one. That test showed me stopwords aren't just about ranking: if they count, almost no query returns an empty list, so my loop's branch would never fire and criterion 2 would fail. Claude also pointed out that shopping words like "looking", "want" and "size" aren't on the standard list, so I strip those in `agent.py::_parse_query` instead.

**Moment 2**

- *What I asked for:* After writing my acceptance criterias, I asked Claude to read them and suggest me ways to make it sharper.
- *What came back:* Problems I hadn't seen. My "why" for criterion 1 argued for 5 of 5 even though the target is 4 of 5. My size criterion said "no listing has a size other than the one requested," which contradicts my own size rule because `S/M` and One Size are supposed to match "S". My fit card brand check ("names no brand") couldn't actually be checked by string matching, even though my "why" said I only count string-checkable things. It also pointed out that the size test would be too easy to miss if I only called `search_listings` directly, since that already handles the size traps.
- *What I changed:* I tightened the fit card rules myself: hashtags and emoji don't count as sentences, the price has to match as a float, and the platform check is case-insensitive. Then I used Claude's suggestions to give the brand check a fixed list of brand names, list the exact queries and listing ids for each criterion, and run the size test through `python app.py ask`, so my query parser is part of what gets tested.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------- | ------ | ----- | ----- | ----- | ----- | ----- | ------- |
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The selected item is the item the next tools receive | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Size traps | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**How the columns map to my criteria.** criteria.md defines each try as one query (or, for criterion 4, one listing), in the order listed there. `run_eval.py` ran every query 5 times with the cache off. A try is PASS only if all 5 runs of that query passed, so criteria 1, 2, 3 and 5 rest on 25 runs each. Results: [results/run_2026-11-09_1105_before.md](results/run_2026-11-09_1105_before.md) for criteria 1, 2, 3 and 5, and [results/fitcard_2026-11-09_1105_before.md](results/fitcard_2026-11-09_1105_before.md) for criterion 4.

**Earlier invalid attempts, kept as the record.** Three earlier "before" files don't measure the agent. [run_2026-11-09_1048_before.md](results/run_2026-11-09_1048_before.md) ran under a Python without the `mcp` package, so all 80 tries stopped at search with `No module named 'mcp'`. [run_2026-11-09_1049_before.md](results/run_2026-11-09_1049_before.md) and [fitcard_2026-11-09_1047_before.md](results/fitcard_2026-11-09_1047_before.md) ran with an API key the service rejected (`401 UNAUTHENTICATED`), so every model call failed and the agent stopped at `suggest_outfit` with its model-unavailable message. I replaced the key and reran everything with `.venv/bin/python`; the table above is that rerun.

**Real output from one try**, pasted as text, naming the file and function
that produced it:

Criteria 1 and 3, query 1, run 1. Produced by `run_eval.py::main` calling `agent.py::run_agent`:

```
- stopped early: no
- selected_item: Graphic Tee — 2003 Tour Bootleg Style ($24.0, depop)
- search_results: 10

Fit card:
Still can’t believe I scored this 2003 tour bootleg tee for just $24 on Depop. It’s got that beat-up grunge vibe that goes with literally everything. Honestly lived in it all week styled with baggy denim and combat boots.

[1] parse_query
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Graphic Tee — 2003 Tour Bootleg Style, Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey … +7 more
      →    branch: results, continuing
[3] select_item
      out: Graphic Tee — 2003 Tour Bootleg Style ($24.0, depop)
      →    id lst_006
[4] suggest_outfit
      in:  item_id=lst_006, wardrobe_items=10
      out: Hey there! That 2003 tour bootleg tee is an absolute steal for $24 and fits right into your grunge streetwear …
[5] create_fit_card
      in:  item_id=lst_006
      out: Still can’t believe I scored this 2003 tour bootleg tee for just $24 on Depop. It’s got that beat-up grunge vi…
```

Criterion 2, query 1, run 1. Produced by `run_eval.py::main` calling `agent.py::run_agent`:

```
- stopped early: yes — No listings matched 'designer ballgown' in size XXS under $5.00. To find something, raise your price limit above $5, or try a different size or leave the size out, or use broader keywords (for example 'jacket' or 'tee' instead of a specific style).
- selected_item: (none)
- search_results: 0

[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping
```

Criterion 4, listing 2 (lst_002, brand None, $18.0, depop). Produced by `eval_fitcard.py::main` calling `tools.py::suggest_outfit` and `tools.py::create_fit_card`:

```
Score this cute Y2K butterfly baby tee on Depop for just $18 and honestly, I'm obsessed. I've been styling it with baggy jeans and my trusty black jacket for that off-duty model vibe, but it looks just as good dressed down with trousers and combat boots. Such a good little thrift find!
```

Criterion 5, query 1, run 1. Produced by `run_eval.py::main` calling `agent.py::run_agent`:

```
[1] parse_query
      in:  tees size S
      out: {'description': 'tees', 'size': 'S', 'max_price': None}
[2] search_listings (via MCP)
      in:  {'description': 'tees', 'size': 'S', 'max_price': None}
      out: 2 items: Y2K Baby Tee — Butterfly Print, Mesh Long-Sleeve Top — Black
      →    branch: results, continuing
```

Both results are size `S/M`, which contains `S` as a whole token.

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
| - | --------- | ------ | ------- | ------------- |
| 1 | A matching query completes all three tools | 4 of 5 | MET (5/5) | All 25 runs ended with `session["error"]` None and a non-empty `session["fit_card"]`. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | All 25 runs stopped right after search, with `outfit_suggestion` and `fit_card` None and an error naming price, size or keywords. |
| 3 | The selected item is the item the next tools receive | 5 of 5 | MET (5/5) | In all 25 runs the `select_item` id matched the `suggest_outfit` trace id, and no card quoted a dollar figure or platform different from the selected listing's. |
| 4 | The fit card | 4 of 5 | MET (5/5) | All 5 cards are 3 sentences, contain the exact price, and name the platform. None of the 3 brand-None cards names a brand from my list. 0 of 5 have a wrong price or invented brand. |
| 5 | Size traps | 5 of 5 | MET (5/5) | All 25 runs parsed the requested size, and every result had it as a whole token or was One Size. The run log records only result counts and the top 3 titles, so I checked each result's size by calling `search_listings` with the same parsed inputs (it makes no model call and returns the same results every run). |

**Diagnoses**

**No criterion missed.** Every target held on every run: 105 agent runs plus 5 fit cards, all with the cache off.

**Were my targets low?** Partly, yes.

- Criteria 2 and 5 are on the deterministic path (regex parsing and search, no model call), so 5 of 5 was the only sensible target and they were never likely to miss.
- Criteria 1 and 4 allowed one miss for model randomness and quota errors. They got 25 of 25 and 5 of 5, so the allowance wasn't needed this time. I'd tighten **criterion 4**: every card came out exactly 3 sentences with the right price and platform, so 4 of 5 is easy. A stricter version would also check that cards for different items don't read the same way (see below).
- Criterion 5 has an evidence gap: its pass condition depends on each result's size, but the run log doesn't record sizes, so it can't be fully scored from the log alone.

**What the criteria didn't catch.** Reading the output itself turned up two patterns that none of my five criteria measure:

1. **`suggest_outfit` breaks its own length promise.** My Tool Inventory says it returns "under about 120 words", and the prompt says "Keep it under 120 words." In this run, 23 of 60 outfit suggestions (38%) went over 120 words (median 119, longest 146). The mechanism shows in the output: the model spends words on a greeting ("Hey there! That 2003 tour bootleg tee is an absolute steal...") and a sign-off ("Enjoy rocking it!"), then writes two full outfits, and the single "under 120 words" line at the end of the prompt doesn't hold it back. The place is the model's output, but the cause is my prompt.
2. **Fit cards open the same way.** 36 of 60 cards (60%) open with "Score" or "Scored" ("Score this", "Scored these", "Score!"). Every card passes criterion 4, but for different items they read like a template.

Pattern 1 is the one I'm treating as the diagnosis for the improvement. It is a tool not doing what its spec promises, and it is countable from the run log.

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Graphic Tee — 2003 Tour Bootleg Style, Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey … +7 more
      →    branch: results, continuing
[3] select_item
      out: Graphic Tee — 2003 Tour Bootleg Style ($24.0, depop)
      →    id lst_006
[4] suggest_outfit
      in:  item_id=lst_006, wardrobe_items=10
      out: Hey there! That 2003 tour graphic tee is such a cool find and will add an effortless edge to your closet. For …
[5] create_fit_card
      in:  item_id=lst_006
      out: Finally scored this sick 2003 tour graphic tee on Depop for just $24, and it’s giving major grunge energy. Obs…
```

**Empty search**

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping

  No listings matched 'designer ballgown' in size XXS under $5.00. To find something, raise your price limit above $5, or try a different size or leave the size out, or use broader keywords (for example 'jacket' or 'tee' instead of a specific style).

0 model calls this session
```

**Model unavailable** (run with an invalid key passed in as GEMINI_API_KEY for that one command)

```
$ python app.py ask 'baggy jeans'
[1] parse_query
      in:  baggy jeans
      out: {'description': 'baggy jeans', 'size': None, 'max_price': None}
[2] search_listings (via MCP)
      in:  {'description': 'baggy jeans', 'size': None, 'max_price': None}
      out: 3 items: Baggy Carpenter Jeans — Dark Wash, Straight Leg Black Jeans — Faded, Vintage Levi's 501 Jeans — Medium Wash
      →    branch: results, continuing
[3] select_item
      out: Baggy Carpenter Jeans — Dark Wash ($36.0, depop)
      →    id lst_031
[4] suggest_outfit
      in:  item_id=lst_031
      →    model unavailable, stopping

  Found Baggy Carpenter Jeans — Dark Wash, but couldn't write an outfit: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.

1 model calls this session
```

**On the MCP move:** I moved `search_listings` onto the MCP server (`mcp_server.py`), because it is the one tool that doesn't call the model. `run_agent` now calls it through `mcp_client.call_tool`, which shows up as `search_listings (via MCP)` in the trace. `python mcp_client.py` lists the tool with `description: string`, `size: string (optional)` and `max_price: number (optional)`, matching my Tool Inventory. I compared the direct call and the MCP call on 6 inputs, including two that return nothing, and they returned identical lists, still with `price` as a float. Nothing about the return value changed, so my tool was already returning plain JSON-safe data. The one place the seam showed was the environment: the server is a separate process started with the caller's Python, so running the eval outside `.venv` broke every search with `No module named 'mcp'` (see "Earlier invalid attempts" under Run Log, Before). I also added a handler so an MCP failure becomes a message in `session["error"]` instead of a crash.

---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** one prompt, in `tools.py::suggest_outfit`, the branch used when the wardrobe has items (commit `8bf1218`). The last line of the prompt went from

```
Keep it under 120 words.
```

to

```
Hard limit: 100 words in total. No greeting, no sign-off, and no opinion on whether to buy it. Start directly with the first outfit.
```

I aimed at 100 rather than 120 so normal variation still lands under the 120 my Tool Inventory promises. I left the empty-wardrobe prompt alone, because all 5 of its outputs in the before run were already under 120 words. Nothing else changed: same scenarios, same model, temperature 0.9, cache off.

**Which failure it was meant to fix:** diagnosis pattern 1. `suggest_outfit` broke its own length promise in 23 of 60 outputs, because the model spent words on a greeting and sign-off and the one soft "under 120 words" line didn't hold it back.

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------- | ------ | ----- | ----- | ----- | ----- | ----- | ------- |
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The selected item is the item the next tools receive | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Size traps | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Same column mapping as the before run (each try is one query, PASS only if all 5 runs of it passed). Results: [results/run_2026-11-09_1115_after.md](results/run_2026-11-09_1115_after.md) and [results/fitcard_2026-11-09_1115_after.md](results/fitcard_2026-11-09_1115_after.md).

**Did it help, and how do I know:** yes, on the thing it was aimed at, and it broke nothing my criteria measure.

| Measure | Before | After |
| ------- | ------ | ----- |
| Criteria met | 5 of 5 | 5 of 5 |
| Outfits over 120 words (example wardrobe, 55 outfits) | 23 | 0 |
| Outfit length, min / median / max words | 94 / 119 / 146 | 65 / 79 / 97 |
| Outfits opening with a greeting ("Hey there!") | 45 of 50 | 0 of 50 |
| Outfits naming at least 2 wardrobe pieces exactly | 50 of 50 | 50 of 50 |
| Output tokens for the whole `run_eval.py` run | 13,055 | 9,157 |

The before numbers come from [results/run_2026-11-09_1105_before.md](results/run_2026-11-09_1105_before.md) and [results/fitcard_2026-11-09_1105_before.md](results/fitcard_2026-11-09_1105_before.md). Every outfit is in those files, so the word counts can be checked by counting the text there. The outfits got shorter without losing what they're for: each one still names at least 5 pieces from the wardrobe by their exact names. One example from the after run (criterion 1, query 1, run 1, from `tools.py::suggest_outfit`):

```
Outfit One: Pair the graphic tee with baggy straight-leg jeans, dark wash and black combat boots. Layer the vintage black denim jacket on top and finish with the black crossbody bag for an effortless, grunge-inspired streetwear look.

Outfit Two: Tuck the graphic tee into the wide-leg khaki trousers. Cinch the waist with the brown leather belt, and wear it with the chunky white sneakers for a cool, casual high-low contrast.
```

Two things I did not expect. Fit cards opening with "Score" or "Scored" dropped from 36 of 60 to 17 of 60, even though I didn't touch the fit card prompt. The card is written from the outfit text, and the outfit no longer starts with "...is an absolute steal", so that is the likely reason, but I haven't tested it. And the output token count fell by about 30%, so each run is also cheaper.

---

## What's Still Broken

No criterion is missed, so these are things my criteria don't catch:

- **The empty-wardrobe outfit can still go over 120 words.** I didn't change that prompt, and in the after run one of its 5 outputs was 124 words (before: 102 to 115). The same prompt change would very likely fix it. I left it out to keep the improvement to one change.
- **Fit cards still sound alike.** 17 of 60 cards still open with "Score" or "Scored". Criterion 4 doesn't measure variety, so I'd add a check such as "for 5 different items, no two cards share their first two words", and then give the fit card prompt an instruction about openings.
- **Criterion 4 is easy to pass.** Every card in both runs was exactly 3 sentences with the right price and platform, so 4 of 5 is a low bar. Tightening it to 5 of 5, plus the variety check above, would make it worth measuring.
- **Criterion 5 can't be scored from the run log alone.** The trace prints only the top 3 result titles, not each result's size, so I checked sizes by calling `search_listings` directly. Logging every result's size in the trace would fix that.
- **Query parsing edge cases.** `'size M/L top'` reads the size as `M` and leaves `L` in the search words, and `'tee under 30 dollars'` leaves `dollars` in. Neither is in my criteria. Search still returns sensible results for both, but they show the regex parser only handles the phrasings I wrote it for.

<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
