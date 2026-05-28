# Promptiv Product Brief

> **What this document is:** The product's emotional and editorial north star. Reference this when making judgment calls that specs don't cover — microcopy, defaults, UI density, edge-case handling, voice. When something doesn't feel right, check it against this brief.
>
> **What this document is not:** A feature spec. Specs tell you *what* to build. This tells you *what it should feel like* and *how to judge* whether an implementation choice serves that feeling.

---

## 1. The core feeling: relief

Most travel tools make users feel *capable but exhausted*. Kayak makes users feel like search analysts. Google Flights makes them feel like optimizers. Going makes them feel like they have homework. Hopper makes them feel like they're playing a slot machine.

**Promptiv should make users feel relief.** The relief of someone else having already done the thinking. The relief of not needing to know what they don't know. The relief of being told the truth.

That's the emotional center. Every other principle in this document flows from it.

---

## 2. The internal monologue

When using Promptiv, the user's internal narration should sound like this:

- *"Oh wait, that's actually doable."*
- *"Huh, I never would've thought of that."*
- *"Okay, this one's honest — they're telling me it sucks in August."*
- *"This isn't trying to sell me anything."*

It should **not** sound like:

- *"I'm getting a great deal."* (Promptiv is not a deals product.)
- *"I'm winning at travel."* (Promptiv is not a power-user tool.)
- *"There are so many options."* (Overwhelm is the enemy.)

The emotional payoff is **permission**, not triumph. Permission to take a trip the user wasn't sure they could take.

---

## 3. The product metaphor

Promptiv is **a knowledgeable friend who travels a lot and has no skin in the game.**

That friend:

- Doesn't dump 200 results on you. Gives you five trips, labeled by archetype.
- Doesn't speak in marketing copy. Speaks in specifics: *"The flight lands at 1am." "Don't go in August, it's a sauna." "The beach in the photos isn't the one you'll be on."*
- Isn't trying to maximize your bookings. Is trying to make sure you don't waste your vacation.
- Will tell you not to go somewhere. Occasionally and clearly.

If an implementation choice would make Promptiv feel like a *search engine*, a *deal site*, or a *travel agency* — it's wrong. If it would make Promptiv feel like *that friend* — it's right.

---

## 4. Editorial principles

These are non-negotiable. They apply to all user-facing text: microcopy, catches, vibe tags, result labels, error states, empty states.

### 4.1. Specificity over adjectives

Every adjective is suspect. Replace with facts.

- ❌ "Chilly evenings" → ✅ "45°F at night"
- ❌ "Crowded in peak season" → ✅ "Cruise ships dock three days most weeks"
- ❌ "A long flight" → ✅ "11 hours minimum, usually with a connection"
- ❌ "Some safety concerns" → ✅ "State Department flags Zones 1 and 18"

### 4.2. Lead with the catch, not a hedge

When telling the user something inconvenient, say it first. No "while X is wonderful, you should know…" framing. The user is here for honesty, not a buffer.

- ❌ "Mexico City is amazing, though it's a city not a beach."
- ✅ "It's a city, not a beach."

### 4.3. Second-person, present tense

The user is being addressed directly, not described.

- ❌ "Travelers will find that..."
- ✅ "You'll land at 1am."

### 4.4. Banned vocabulary

These words mean nothing and signal marketing copy. They should not appear anywhere in user-facing text:

- *vibrant, bustling, charming, hidden gem, must-visit, breathtaking, stunning, gateway to, off the beaten path, immersive, authentic, world-class, picturesque, magical, idyllic*

If a sentence falls apart when these words are removed, the sentence wasn't carrying real information.

### 4.5. Restraint over enthusiasm

Promptiv is not excited for the user. It is *useful* to the user. Excitement reads as a sales pitch and breaks trust. The tone is closer to a respected travel writer than a brand voice.

---

## 5. The trust contract

Promptiv's entire differentiation rests on **honesty**. This is not a soft principle — it's the product's only moat.

### 5.1. The catch is the trust mechanism

Every destination has a `base_catch` — a specific, honest downside. This field is the single most important text in the product. If catches read like marketing ("a charming colonial town with some quirks"), the trust contract breaks and the rest of the product loses its credibility.

A good catch makes the user think: *"They're being real with me."* A bad catch makes the user think: *"This is just a travel site."*

### 5.2. The "Don't Do It" card is signature

Some result sets should include a "Don't Do It" card — a destination that's technically cheap or technically a match, but that the user would regret. Examples:

- A $198 round trip that requires two layovers and a 5:40am departure.
- A beach destination booked into hurricane season.
- A city the user picked for nightlife that's in Ramadan during their dates.

Showing the user what *not* to book is what makes everything else credible. It's the same psychology as a critic who pans something: their praise becomes worth more.

### 5.3. Never optimize for booking volume

Promptiv has no booking integration in v1. Don't pretend it does. Don't add fake urgency ("3 people viewing this!"), countdown timers, "deal expires" framing, or any pattern borrowed from OTAs. These break the trust contract instantly.

---

## 6. Output design principles

### 6.1. Five to seven results, never more

A user with a budget and a date window does not want 47 destinations. They want a small set they can actually decide between. The output ceiling is **7 cards. Default is 5.** Going higher dilutes the feeling that someone *picked* these trips.

### 6.2. Results are labeled by archetype, not ranked

Cards are categorized — *The Easy Yes, The Cheap Escape, The Wild Card, The Stretch Pick, The Smart Pick, The Don't Do It* — not numbered #1 through #5. Archetypes communicate *what kind of trip this is* in one glance. Numbered ranks communicate optimization, which is the wrong frame.

### 6.3. Each card must answer five questions

Every card, regardless of archetype, surfaces:

1. **Where** (city, country)
2. **What it costs** (price + baggage-adjusted estimate)
3. **When** (dates, travel time, stops)
4. **Why it fits** (one sentence, references the user's inputs)
5. **What the catch is** (one sentence, specific and honest)

If a card is missing any of these, it fails the trust contract.

### 6.4. Cards should feel earned, not generated

Even though output is algorithmic, it should read like someone *picked* these for this user. The way to achieve this:

- **Specificity in the catch.** Generic catches kill the feeling.
- **Restraint in count.** 5 picks feel chosen. 25 feel scraped.
- **Opinion in the labeling.** "The Easy Yes" is opinionated. "Top Result" is not.
- **No filler.** If only 4 destinations deserve a card, show 4. Don't pad.

---

## 7. UI and interaction principles

### 7.1. Calm, not busy

The interface should signal "we did the work, you just look." Not "complex tool, work hard."

- Generous whitespace.
- Editorial typography (think long-form magazine, not data dashboard).
- Cards that feel like postcards or recommendations, not search rows.
- No sidebars of filters competing with results.
- No data-table density.

If a screenshot of the results page looks like Kayak or Skyscanner, it's wrong.

### 7.2. Inputs should feel like a conversation

Even though the input form is structurally a form, microcopy matters. The framing should sound like a knowledgeable friend asking, not a database collecting.

- ❌ "Trip duration (days)" → ✅ "How long can you escape?"
- ❌ "Max budget (USD)" → ✅ "What can you spend?"
- ❌ "Origin airport (IATA)" → ✅ "Where are you flying from?"

### 7.3. Defaults should reflect reality

Default values communicate the product's assumptions about the user. They should assume:

- The user has a job and limited PTO.
- The user is price-aware but not desperate.
- The user wants a trip, not a stunt.

Concretely: default trip length 4-5 nights, default bag preference "carry-on," default max stops 1, default departure window "next 90 days."

### 7.4. Refinement is optional, not required

Front-load delight, back-load configuration. The first input pass should be the minimum needed to return useful results. Filters like "max stops," "max travel time," "bag preference" live behind a "Refine these results" affordance — not on the main form. A user should be able to get to results in under 30 seconds.

---

## 8. What "success" looks like for a user session

A user who has a successful session with Promptiv:

1. Spends **under 30 seconds** entering inputs.
2. Reads **all 5-7 cards** (not just the first one).
3. Has at least one moment of *"huh, I never would've thought of that."*
4. Trusts at least one catch enough to **decide against** a destination they were drawn to.
5. **Screenshots a card and texts it to someone** ("look what came up").
6. Comes back **months later** when planning the next trip — not because of a subscription or alert, but because they remember Promptiv was honest with them.

Note what's not on this list: spending hours configuring, setting up deal alerts, building a watchlist, comparing to other sites. **Promptiv wins when users use it briefly, trust it deeply, and remember it later.** Optimizing for traditional engagement metrics is antithetical to the product.

---

## 9. Decision rules for implementation

When making a judgment call not covered by specs, use this hierarchy:

1. **Does this serve the feeling of relief?** If a choice adds cognitive load, configurability, or noise — default against it. Promptiv removes work from the user; it doesn't add it.

2. **Does this protect the trust contract?** If a choice borrows a pattern from OTAs (urgency, fake scarcity, hidden fees, dark patterns, marketing language) — reject it, even if it would improve conversion in the short term. The trust contract is the only moat.

3. **Would a knowledgeable friend do this?** Imagine handing the choice to a friend who travels a lot and has no skin in the game. Would they recommend it? Would they say it that way? Would they show that many options? If not, neither would Promptiv.

4. **Is it specific?** If a string, label, or value reads as generic — it's wrong. Make it specific or cut it.

5. **When in doubt, do less.** Fewer results. Fewer fields. Fewer features. Promptiv's value is in restraint.

---

## 10. Red flags

If any of the following are true of an implementation choice, stop and reconsider:

- A result set shows more than 7 cards.
- A catch contains the word "vibrant," "charming," "hidden gem," or similar.
- Microcopy reads like it was written by a marketing team.
- The UI is starting to look like Kayak.
- A feature exists to drive engagement rather than utility.
- The product is excited for the user instead of useful to them.
- An adjective is doing work a fact should be doing.
- The user has to click "Show more" to see a real recommendation.
- Booking-flow patterns (urgency, scarcity, countdown) appear anywhere.
- A result card is missing the catch.

---

## 11. One-sentence summary

> Promptiv is a knowledgeable friend with no skin in the game who tells you five trips you can actually take, why each one fits, and what the catch is — and occasionally tells you not to go.

Every implementation choice should be checkable against that sentence.

---

## 12. The mechanic behind the feeling

Sections 1-11 describe how Promptiv should feel and read. This section describes what it *does* that nothing else does — the structural reason it can deliver the feeling at all.

### 12.1. The inversion is the moat

Every other travel tool asks the user a forward question:

- Google Flights, Skyscanner: *"Where to and when? I'll find a fare."*
- Going, Hopper: *"Where to and what budget? I'll alert you when prices drop."*
- Kayak: *"Where to and when? I'll show you the matrix of options."*

Promptiv asks the inverse:

- *"What can you spend and when can you go? I'll find destinations."*

The user arrives with constraints, not a destination. The product converts those constraints into a small set of places the user can actually go.

This is the structural differentiator. Everything else in this brief — the editorial voice, the catches, the curation, the calm UI — exists to make the inverted results feel chosen rather than generated. The inversion is what the product *is*. The rest is what the product *feels like*.

### 12.2. The curated destination set is the flagship tier, not the universe

The hand-curated destinations in `destinations.yaml` are not the menu of available destinations. They are the destinations where Promptiv has rich editorial knowledge: voice catches, vibe tags, novelty scores, season notes.

The system can return any destination the flight API surfaces. Curated destinations get richer cards. Uncurated destinations get a structured catch and the flight-derived catch (see 12.3) — still useful, still honest, just less editorial flavor.

The curated set should grow toward destinations users are actually getting recommended, not toward a pre-built guess. The expansion path tracks actual demand, not curator intuition.

### 12.3. The catch is a two-layer synthesis, not a single field

The catch shown on each card is composed from two sources.

**Layer A — Destination layer (curated, global, slow-changing):**
The destination's `base_catch` field. Hand-written for the editorial flagship set. Honest, specific, in the voice rules from section 4. Examples:

- *"It's a city, not a beach. February nights drop to 45°F."*
- *"Cruise ships dump 5,000 day-trippers a day in peak season."*

**Layer B — Flight reality layer (computed, per-search):**
Derived from the specific flight result for this user. Computed from departure hour, total travel time, layover count, baggage realism. Examples:

- *"From your origin: one stop in Miami, 8h20m total. Cheapest fare departs at 5:40am."*
- *"3 stops, 22h door-to-door for a 4-night trip."*

Voice rules from section 4 apply to BOTH layers equally. The flight reality layer is computed but must read in the same restrained, specific, second-person voice. No adjectives doing fact-work. No marketing fluff bleeding in through the computation.

On the card, the two layers combine. When both have something to say, both appear. When only one has something to say, that one carries the card. When neither does (well-curated destination with unremarkable routing), the card shows just the price, dates, and "why it fits."

### 12.4. "Don't Do It" is algorithmic, not hand-picked

The "Don't Do It" archetype card from section 5.2 can be computed from flight data. A trip is *Don't Do It* when it scores high on cheapness AND high on travel pain: long total travel time, brutal departure hour, multiple layovers, tight return on a short trip.

The system identifies these per-search, not from a hand-curated list. This is what makes "Don't Do It" scalable. It's also what makes it credible: the system isn't pretending to know better than the user, it's surfacing a result that is technically cheap but practically miserable and labeling it as such.

### 12.5. Origin handling is structural, not editorial

Any origin works because:

1. The flight API knows the route from any origin.
2. Destination metadata is origin-agnostic.
3. The flight-derived catch tells the truth about routing for this specific user.
4. The destination layer catch tells the truth about the place itself.

No hub gating. No "drive to your nearest major airport" prompts. A user from Tucson gets the same product as a user from JFK. The catches and rankings adjust automatically because the flight data adjusts automatically.

### 12.6. What this means for build priorities

The brief implies a hierarchy of engineering risk:

1. **The inversion engine is critical-path.** Flexible-date, multi-destination, budget-first search across an arbitrary origin must work reliably. If this fails, nothing else matters.
2. **The catch synthesis layer is brand-critical.** Both the curated destination catch and the computed flight catch must follow section 4 voice rules without drift.
3. **The curated destination set is leverage, not foundation.** Expanding it improves quality on common destinations but isn't a precondition for the product working.

The previous v1 architecture (12 hubs × 100 destinations, hard-coded origin dropdown) solved the wrong problem. It defended a curation moat that isn't the moat. The actual moat is the inversion. Origin restriction was unnecessary friction.
