# Promptiv — Product Brief

Initial draft co-developed with ChatGPT, captured 2026-05-25 during brainstorming with Claude Code (Adam).

---

## Product

Promptiv Trips — a trip discovery product for normal people, not a power-user flight intelligence tool.

The core customer is not someone who wants to tweak airline alliances and layover windows. The core customer is someone thinking:

> "I want to go somewhere, but I don't know where I can actually afford."

That is the emotional hook.

## Positioning

**Promptiv finds real trip ideas based on your budget, calendar, and travel mood.**

Not a flight search engine. A flexible trip discovery engine for people who know their budget, not their destination.

## Killer feature

> "I have $___ and ___ days. Where can I go?"

Example: "I have $500 and 4 days in August. I'm flying from Nashville. I want warm, fun, and not exhausting."

Returns 5-10 trip cards:
- Best Overall Trip
- Cheapest Escape
- Best Beach Option
- Best Food City
- Wild Card
- Worth Stretching For

Each card shows: Price, Dates, Stops, Travel time, Baggage-adjusted estimate, Why it fits, **What's the catch**, Suggested trip style.

The "what's the catch?" line is part of the trust-building. Promptiv tells you when not to buy.

## Inputs (user side)

- Home airport
- Budget
- Available dates or general month
- Trip length
- Vibe
- Passport yes/no
- Max travel pain (easy / okay / adventurous)
- Bags / carry-on preference
- Max stops

## Result categories (personality layer)

- **The Easy Yes** — best low-stress option
- **The Cheap Escape** — cheapest solid trip
- **The Wild Card** — unexpected but interesting
- **The Stretch Pick** — a little above budget but maybe worth it
- **The Smart Pick** — best balance of price, timing, destination quality
- **The Don't Do It** — technically cheap but miserable (signature feature; builds trust)

## Promptiv Score (the moat)

Not just cheapest. Best fit. Scored on:
- Price vs budget
- Trip length fit
- Number of stops
- Departure / arrival times
- Total travel duration
- Baggage realism
- Destination vibe match
- Passport requirement
- Season / weather fit
- Ease for a normal traveler

## Headline candidates

**Preferred:** Find the trip hiding in your budget.

Subhead: Enter your home airport, dates, budget, and vibe. Promptiv searches real flight data to uncover trips you can actually take.

Buttons: Find My Trip / Spin Trip Ideas

Alternatives:
- "You don't need to know where you're going. Just know what kind of trip you want."
- "Tell us your budget. We'll show you where it can take you."

## MVP scope

One strong workflow: **Flexible Trip Finder**.

Behind the scenes: maintain a destination list, run flexible-date searches across it, rank with Promptiv Score.

Output: 5-10 trip cards.

## Monetization

**Free:** 3 searches/month, limited destinations, basic trip cards.

**Pro ($7-9/month):** Unlimited searches, weekend trip finder, international trip finder, baggage-inclusive pricing, saved searches, flexible month search, multi-city ideas, deal alerts (later), shareable trip boards.

**One-time option — Trip Shortlist ($9):** User pays once to get a curated list of 10 trip ideas for a specific budget/date window. May convert better than subscription at first.

## Technical foundation

Built on `fli` (Google Flights reverse-engineered CLI/library/MCP — installed today). Capabilities the MVP relies on:
- Cheapest date windows (`fli dates`)
- Specific-date searches (`fli flights`)
- Multi-city (`fli multi`)
- Baggage-inclusive pricing (`--bags`, `--carry-on`)
- Airport resolution (`fli airports`)
- JSON output for app-layer wrapping

## Why this over the alternative ("power-user flight intelligence tool")

Power-user flight intelligence competes with Google Flights / Skyscanner / ITA Matrix / Going / Seats.aero — crowded space, customers who already know what they want.

Normal-person trip discovery has a clearer emotional gap:
- People want to travel
- They don't know where to go
- They don't know what's realistic
- They get overwhelmed
- They quit searching

Promptiv solves the "blank page" problem of travel.
