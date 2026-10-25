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
| 1.        |        |       |       |       |       |       |         |
| 2.        |        |       |       |       |       |       |         |
| 3.        |        |       |       |       |       |       |         |
| 4.        |        |       |       |       |       |       |         |
| 5.        |        |       |       |       |       |       |         |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

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
| 1 |           |        |         |               |
| 2 |           |        |         |               |
| 3 |           |        |         |               |
| 4 |           |        |         |               |
| 5 |           |        |         |               |

**Diagnoses**

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

```

**Empty search**

```

```

**On the MCP move:**

---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------- | ------ | ----- | ----- | ----- | ----- | ----- | ------- |
| 1.        |        |       |       |       |       |       |         |
| 2.        |        |       |       |       |       |       |         |
| 3.        |        |       |       |       |       |       |         |
| 4.        |        |       |       |       |       |       |         |
| 5.        |        |       |       |       |       |       |         |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->

---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

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
