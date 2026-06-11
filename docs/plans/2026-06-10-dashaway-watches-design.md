# DashAway Watches — Design (approved)

**Status:** Design approved 2026-06-10. Implementation plan not yet written.
**One-liner:** *"Tell us the trip you're dreaming about. We watch it every night and email you when it's time to book."*

## Why this product (the strategic logic)

Interactive flight search cannot be a public product on our infrastructure: Google 429-blocked a fresh datacenter IP after ~6 interactive searches (proven 2026-06-10 on flights.distillworks.com), and arbitrary origin×dest×date coverage cannot be pre-computed (billions of pairs). Every workaround (proxies, SerpAPI, GDS APIs) costs money, legitimacy, or the budget-carrier coverage that produces our headline results (GDS misses Allegiant/Spirit — the $86 BNA→GRR nonstop would not exist in Amadeus).

The inversion: **design for scarce, slow, batched requests instead of fighting them.** The product where that's natural is the *watch* — async by nature, batch by design, and the accumulating observation history becomes a moat nobody can rent ("lowest in 47 nights of watching" is only sayable by someone who was watching).

Key primitive: `SearchDates` returns ~180 date-pairs across ~6 months in ONE request. One paced request per route per night covers a traveler's entire flexible window.

Structural decisions (all user-approved):
- **DashAway tier**, not a standalone product. Watches is DashAway's missing retention layer (the site is currently read-only). Funnel: hubs/digest (discovery, "where could I go") → watch (intent, "tell me when") → paid watches (later). Digest = the broad "anywhere" net; Watch = the sharp "my exact trip" pole. Same archive underneath.
- **Coverage grows along demand:** any US origin allowed (not just the 12); watch fares write into `fare_observations`, so users expand the archive exactly where demand is. This answers "12×99 isn't enough" without guessing destination lists.

## The watch

```
WATCH = {
  origin:   any IATA in fli's Airport enum (e.g. BNA)
  dest:     any IATA (e.g. PLS)
  window:   flexible date range, max ~6 months (e.g. Nov 1 – Jan 31)
  nights:   single value (default 7; ranges deferred — they multiply requests)
  ceiling:  optional $ threshold
  email:    identity (no accounts)
}
→ exactly 1 SearchDates request per night
```

## User journey

`dashaway.io/watch` form → **double opt-in confirmation email** (deliverability + junk protection) → live that night → emails only per the alert brain → every email carries a **tokenized manage link** (pause/edit/delete; no login; same pattern as unsubscribe tokens). **v1 enforces 1 active watch per email**; UI hints "more watches coming soon."

## Alert brain (the product's soul) + covenant

Triggers (any fires → alert):
- **night 2+:** cheapest-week price drops ≥12% vs trailing low
- **night 14+:** current best enters bottom 15% of all observations for this watch (same 14-day maturity gate as the digest's deal alerts — one consistent philosophy)
- **anytime:** crosses the user's ceiling

Covenant: **≤1 alert per watch per week**, override only on a ≥20% single-night drop. Plus one **weekly pulse** line per watch in the Sunday digest: "Watched 47 nights · best week Dec 9–16 at $389 · trending ↓" — the retention organ; proof the watching is real between alerts.

## The alert email

Subject: `↓ $325 — your Turks & Caicos trip`
Body = the BEST-card treatment (from the flightcompare web UI): price, exact week, "lowest in 47 nights, bottom 8% of everything we've seen", flight numbers when nonstop, **all-in week framing when dest is in the curated catalog** ("$325 flight → about $2,075 all-in for the week" — the DashAway signature no competitor has), Google Flights deep link to act, honest footer (prices move; verify before booking).

## Engine & data

- New systemd timer **`promptiv-watches` ~03:00 UTC**, finishing before the 07:00 refresh; zero interaction with the existing run.
- Dedupe watches → distinct (route, window, nights) → one paced `SearchDates` each (~10–15s incl. politeness gap) → write `fare_observations` → evaluate triggers → queue emails (Resend, existing infra).
- Runtime math: 100 watches ≈ 25 min · 500 ≈ 2h · the 03:00–06:30 slot fits ~800 before rethinking.
- New tables in the DashAway SQLite: `watches` (email, origin_iata, dest_iata, window_start, window_end, trip_nights, ceiling_usd, status, token, created_at, confirmed_at, last_alert_at), `watch_events` (alert log; powers the 1/week throttle).
- Watch fares land in `fare_observations` with **`source='watch'`** so refresh data and watch data stay distinguishable in the archive.

## Validation bounds (form + API)

- `trip_nights`: single integer 3–14, default 7.
- Window: `window_start` ≥ tomorrow · span ≤ 185 days (proven SearchDates range) · `window_end` ≤ 300 days out.
- Airports: must exist in the fli `Airport` enum; origin ≠ dest.
- Drop trigger precisely: tonight's best ≤ 88% of the **trailing 14-night low** (not all-time low — keeps the trigger responsive after a price regime change).

## Pulse delivery note (refinement)

The approved sketch said "pulse line in the Sunday digest," but watch users are not necessarily digest subscribers. v1: the weekly pulse is its **own short Sunday email** to watch users (reuses the digest send machinery). Merging it into the city digest for users who have both comes later.

## Ops guardrails (the no-cap compensation)

User chose **no user-facing capacity cap; monitor instead**. Compensating tripwires:
- Nightly ops summary email: watches run, errors, runtime, growth count.
- Hard alarms: runtime >3h, error rate >10%, **any 429 → the job stops for the night** (never retry into a block; protects the refresh sharing the IP).

## Anti-abuse

Double opt-in · 1 watch/email · per-IP creation rate limit on the form · IATA validation against the fli enum.

## Monetization (designed, NOT built)

v1 free, 1 watch. Paid tier later: more watches at a very low price point (user direction: ~$0.99/mo). **Flag on record:** Stripe's $0.30 + 2.9% eats ~37% of a $0.99 monthly charge; $9.99/yr delivers the same psychological cheapness at ~6% fee drag with no monthly churn ops. Decide at build time.

## Explicitly NOT in v1

Payments · multi-destination watches · exact-date watches · nights ranges · SMS · accounts · **any interactive fare fetching anywhere** · fare *predictions* ("prices will rise") — we report observed history only, never forecasts; honesty is the brand.

## Success criteria (30 days post-launch)

≥25 confirmed watches from ≥15 non-Adam emails · alert open rate ≥45% · ≥1 "I booked it" reply · zero 429 incidents · nightly error rate <5%.
Diagnosis map: no watches created → the form/promise failed; watches but unopened alerts → the brain failed.

## Risks (plainly)

- Google fragility becomes a **revenue** dependency, not just SEO (mitigated by tripwires, not eliminated).
- Cold-start trust: digest list + hubs are the seed audience.
- Going/Hopper could ship flexible-window watches; wedge = exact-trip + flexible window + percentile honesty + all-in cost + indie voice.
- Alert quality unprovable until ~14 nights of history; the weekly pulse must carry perceived value in the gap.

## Related assets

- `~/flightcompare/` — flc CLI (personal interactive tool, stays as the lab) + the web UI at flights.distillworks.com (BEST-card rendering to reuse in emails; interactive search there is dead due to the 429 block, which seeded this design).
- `fare_observations` / nightly refresh / digest engine / Resend / unsubscribe-token pattern — all reused.
