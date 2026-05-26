# Promptiv v1 Design Spec

**Status:** Draft for user review 2026-05-26
**Author:** Adam Shontingh + Claude
**Supersedes:** N/A (v0 was the teaser at promptiv.io, which becomes the email-capture layer for this v1)

---

## 1. Purpose

Promptiv v1 is a trip-discovery product that owns the "blank page" problem in travel planning. The killer query is:

> "I have $X and Y days. Where can I go from [my airport]?"

Existing tools require the user to already know the destination (Google Flights), gate discovery behind subscriptions (Going.com), or hide flexible search in second-class UX (Skyscanner Everywhere). Promptiv surfaces honest, ranked trip ideas with explicit "what's the catch" reasoning for each.

### Success criteria for v1 launch

- 100 destinations curated with full structured data + catch text
- 12 origin airports covered (~70% of US flyers)
- ~50 origin/destination route pairs with route-specific catch overlays (only the routes that genuinely surface in /go results)
- Interactive /go workflow returns 5-8 ranked trip cards in <500ms (using cached prices)
- Nightly fli refresh completes in <8 hours, <5% route failure rate
- Email capture rate >25% at the 5-search gate
- A reasonable share of visitors run >1 search (sticky tool hypothesis validates)

### Non-goals for v1

- **Programmatic SEO pages** (deferred to v1.1, see §9)
- Booking (always deep-links to Google Flights)
- Pro tier ($7/mo paid plan) (deferred to v1.1)
- Hotels, cars, activities
- Mobile native app
- Multi-passenger or family trip planning
- Account system with saved trips (session-cookie only in v1)
- Real-time price updates (cached nightly data only)

---

## 2. Persona

**v1 is built for: young flexible traveler.**

- Age 22-35
- US-based, departing from a major hub
- Budget-constrained ($300-$1,500 typical for international, $100-$500 domestic)
- Time-flexible (can shift dates ±2 weeks for better prices)
- Novelty-driven (will say yes to a place they've never heard of)
- Tolerates inconvenience for value (red-eyes, layovers, off-season)
- Travels 1-3 times per year, plans 1-8 weeks ahead
- Discovers via TikTok/Instagram/Reddit, books via web

**What this persona means for design choices:**

- Catch voice can be blunt ("you'll be wrecked"). They self-identify as someone who can handle the truth and rewards honesty.
- Mobile-first UX. Desktop is secondary.
- No login required. Login friction kills impulse discovery.
- Ranking weights novelty over comfort.
- SEO traffic on "where can I go for $X" queries matches their search behavior.

---

## 3. User flows

### Flow A: Interactive /go (the killer feature)

```
1. User lands on /go (linked from / and SEO pages)
2. Form fields:
   - Home airport (dropdown of 12 hubs, defaults to none)
   - Budget ($ input, defaults to "500")
   - Trip length: 3 buttons (short 5n / medium 7n / long 10n), defaults to medium. Must match cached values (see §6).
   - Vibe chips (multi-select, 0-7 chips, default none = all)
3. User submits → POST /api/go
4. Backend:
   - Joins price_snapshots × destinations
   - Filters by origin_iata, total_price ≤ budget, trip_nights = selected
   - Applies vibe filter (intersection)
   - Ranks (see §7)
   - Returns top 8
5. Frontend renders 8 cards (see §8)
6. Session counter increments. If >= 5, next submit triggers email gate.
```

### Flow B: Email gate

```
1. User submits 5th /go search in session (tracked via session cookie + searches table)
2. Backend returns results with email_gate_active=true
3. Frontend overlays modal on 6th attempt:
   "We're tracking 14 ideas you've explored. Drop an email and we'll send the
    next batch when prices shift."
4. Email submit → POST /api/signup (existing teaser endpoint)
5. Modal dismisses, session.email_gate_satisfied = true, unlimited searches resume
```

---

## 4. Architecture

### Stack (no changes to existing infrastructure)

- **Web**: Flask 3.0.3 on gunicorn 23.0.0 (existing)
- **DB**: SQLite at `/var/lib/promptiv/teaser.sqlite` (existing, gains 5 new tables)
- **Email**: Resend (existing)
- **Flight data**: fli (`mcp__fli__*` or `flights` Python package called from cron script)
- **Reverse proxy**: nginx (existing, gains routing for /go, /from, /destination)
- **Cron**: systemd timer (new), runs `cron_refresh_prices.py` nightly at 02:00 Central
- **Static assets**: served from `/srv/promptiv/public/` (existing)

### New components

```
~/promptiv/
├── server/
│   ├── app.py                   (existing, gains /go route + /api/go endpoint)
│   ├── db.py                    (existing, gains queries for new tables)
│   ├── email_client.py          (existing, unchanged)
│   ├── migrations.py            (existing, gains new tables)
│   ├── destinations.py          (NEW: load destinations.yaml + routes.yaml into DB)
│   ├── ranking.py               (NEW: scoring formula)
│   ├── fli_client.py            (NEW: wrapper around fli Python package)
│   ├── price_refresh.py         (NEW: cron entry point)
│   └── catch.py                 (NEW: compose base_catch + route_catch_text)
├── data/
│   ├── airports.yaml            (NEW: 12 hubs, hand-curated)
│   ├── destinations.yaml        (NEW: 100 destinations, hand-curated)
│   └── routes.yaml              (NEW: ~50 route_catch_text overrides for high-surface routes)
├── public/
│   ├── go.html                  (NEW: interactive search form + results)
│   ├── index.html               (existing teaser, updated to drive to /go)
│   ├── styles.css               (existing, gains /go styles)
│   └── app.js                   (existing, gains /go form handler)
├── deploy/
│   ├── promptiv-refresh.service (NEW: systemd unit for cron)
│   └── promptiv-refresh.timer   (NEW: systemd timer)
└── docs/superpowers/specs/2026-05-26-promptiv-v1-design.md  (this file)
```

### Request flow

```
Browser → nginx → gunicorn → Flask
                              ↓
                              ├── /              → index.html (landing, links to /go)
                              ├── /go            → go.html + POST /api/go
                              ├── /api/signup    → existing
                              └── /api/healthz   → existing

Cron (systemd) → price_refresh.py → fli_client → Google Flights (reverse-engineered)
                                          ↓
                                          → SQLite price_snapshots
```

---

## 5. Data model

### Existing tables (unchanged)

- `signups (id, email, created_at, ip_hash, referrer)` — email gate writes here
- `qualifiers (signup_id, budget_bucket, home_airport, frustration, created_at)` — unchanged

### New tables

```sql
CREATE TABLE airports (
    iata TEXT PRIMARY KEY,           -- 'BNA'
    city TEXT NOT NULL,              -- 'Nashville'
    state TEXT,                      -- 'TN'
    region_us TEXT NOT NULL,         -- 'Southeast'
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    rank_us INTEGER NOT NULL         -- 1-12, for default sort
);

CREATE TABLE destinations (
    iata TEXT PRIMARY KEY,           -- 'CDMX' or composite 'NRT' (use primary IATA)
    city TEXT NOT NULL,              -- 'Mexico City'
    country TEXT NOT NULL,           -- 'Mexico'
    country_code TEXT NOT NULL,      -- 'MX' (ISO 3166-1 alpha-2)
    region TEXT NOT NULL,            -- 'Latin America'
    vibes TEXT NOT NULL,             -- JSON array: ["city","food","history"]
    passport_required INTEGER NOT NULL,  -- 0 or 1
    visa_required_us INTEGER NOT NULL,   -- 0 or 1
    best_months TEXT NOT NULL,       -- JSON array: [1,2,3,11,12] (months 1-12)
    avg_daily_cost_usd INTEGER NOT NULL,  -- food + lodging budget tier
    safety_tier INTEGER NOT NULL,    -- 1=very safe, 4=requires caution
    currency TEXT NOT NULL,          -- ISO 4217
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    base_catch TEXT,                 -- the universal catch about this dest
    novelty_score INTEGER NOT NULL,  -- 1=cliche, 5=most travelers won't know it
    UNIQUE (city, country)
);

CREATE TABLE routes (
    origin_iata TEXT NOT NULL,
    dest_iata TEXT NOT NULL,
    route_catch_text TEXT,           -- nullable: most routes use only base_catch
    PRIMARY KEY (origin_iata, dest_iata),
    FOREIGN KEY (origin_iata) REFERENCES airports(iata),
    FOREIGN KEY (dest_iata) REFERENCES destinations(iata)
);

CREATE TABLE price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_iata TEXT NOT NULL,
    dest_iata TEXT NOT NULL,
    departure_date TEXT NOT NULL,    -- ISO YYYY-MM-DD
    return_date TEXT NOT NULL,       -- ISO YYYY-MM-DD (round-trip only in v1)
    trip_nights INTEGER NOT NULL,    -- 5, 7, or 10
    total_price_usd INTEGER NOT NULL,  -- rounded to whole dollars
    stops INTEGER,                   -- nullable: fli.SearchDates returns only dates+price; v1.1 enriches via SearchFlights
    carrier_codes TEXT,              -- nullable: same as stops; populated in v1.1
    source TEXT NOT NULL,            -- 'fli' for v1
    fetched_at TEXT NOT NULL,        -- ISO timestamp
    FOREIGN KEY (origin_iata) REFERENCES airports(iata),
    FOREIGN KEY (dest_iata) REFERENCES destinations(iata)
);

CREATE INDEX idx_snapshots_lookup ON price_snapshots(origin_iata, total_price_usd, trip_nights, departure_date);
CREATE INDEX idx_snapshots_dest ON price_snapshots(dest_iata, fetched_at);

CREATE TABLE searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,        -- 32-char hex, set as session cookie
    origin_iata TEXT NOT NULL,
    budget_usd INTEGER NOT NULL,
    trip_nights INTEGER NOT NULL,
    vibe_filter TEXT,                -- JSON array, nullable for no filter
    result_iatas TEXT NOT NULL,      -- JSON array of returned dest iatas
    created_at TEXT NOT NULL         -- ISO timestamp
);

CREATE INDEX idx_searches_session ON searches(session_id, created_at);
```

### Why these specific fields

- `novelty_score`: hand-rated 1-5 during curation. Drives the novelty ranking input. Bali = 1 (cliche), Tbilisi = 5 (most won't know it).
- `safety_tier`: 1-4. Doesn't filter results but appears in catch text for tier 3-4 ("US State Department advises caution in tourist areas").
- `best_months` as JSON array: lets a single destination have split seasons (Iceland: 6,7,8 for daylight or 1,2,3 for aurora).
- `routes.route_catch_text` is nullable: only populated when origin matters. ~300 of 1,200 routes will have an override.
- `searches` table is for both analytics and the email gate counter. Sessions are stateless (no users table) in v1.

---

## 6. fli orchestrator

### Cron schedule

- systemd timer: `OnCalendar=*-*-* 07:00:00 UTC` (02:00 Central)
- Service unit calls: `/srv/promptiv/.venv/bin/python -m server.price_refresh`
- Logs to `/var/log/promptiv/price-refresh.log` (rotated daily)

### Algorithm

```python
# Pseudocode for price_refresh.py
def refresh_all_routes():
    routes = db.fetch_all_routes()  # 1,200 (origin, dest) pairs
    trip_lengths = [5, 7, 10]       # nights
    today = date.today()
    window_end = today + timedelta(days=90)

    for origin, dest in routes:
        for nights in trip_lengths:
            try:
                results = fli_client.search_dates(
                    origin=origin,
                    destination=dest,
                    start_date=today,
                    end_date=window_end,
                    trip_duration=nights,
                    is_round_trip=True,
                    sort_by_price=True,
                    currency='USD',
                )
                # results: list of {departure_date, return_date, price, stops, carriers}
                upsert_snapshots(origin, dest, nights, results)
                metrics.success += 1
            except (FliError, RateLimitError) as e:
                log.warning(f"{origin}->{dest} {nights}n failed: {e}")
                metrics.failures += 1
            time.sleep(SLEEP_BETWEEN_CALLS)  # 6 seconds

    log.info(f"Refresh complete: {metrics}")
    if metrics.failures > 0.05 * len(routes) * len(trip_lengths):
        send_alert_email("price refresh failure rate >5%")
```

### Rate limiting strategy

- 6s sleep between calls = ~10 calls/min
- 1,200 routes × 3 lengths = 3,600 calls × 6s = ~6 hours
- If a route fails, skip to next (no retries within same run)
- If failure rate exceeds 5%, alert via Resend email
- Stale data is fine: SELECT logic uses last 7 days of snapshots, displays "as of [date]"

### Snapshot retention

- Keep last 14 days of snapshots per route (DELETE older nightly)
- Average row: ~200 bytes, ~30 snapshots per (origin, dest, nights) per refresh
- Storage estimate: 3,600 routes × 30 prices × 14 days × 200B = ~300MB
- Add monthly VACUUM to reclaim deleted-row space

### Failure modes and recovery

| Failure | Detection | Recovery |
|---|---|---|
| fli returns no results for a route | Empty list from search_dates | Log, skip, retry tomorrow. After 3 consecutive nights of no results, alert (likely a broken route or destination IATA error) |
| fli raises rate limit | Caught exception | Backoff 60s, continue. If 3 consecutive backoffs, abort the run, alert. |
| Google killed fli reverse-engineering | Most/all calls fail | Failure rate alert triggers. Manual intervention: `uv tool upgrade flights`. Users see stale prices, no breakage. |
| Cron doesn't run (systemd issue) | No new fetched_at within 36h | Healthcheck endpoint /api/healthz includes `last_refresh_at`, monitored externally |
| Disk full | DB write errors | Healthcheck shows DB error. Manual: trim old snapshots, increase disk. |

---

## 7. Ranking algorithm

### Inputs to the ranker (per candidate destination)

- `price_usd`: cheapest price for this (origin, dest, trip_nights) in cache
- `budget_usd`: user's submitted budget
- `vibe_overlap`: count of user's vibe chips that match destination.vibes
- `user_vibe_count`: total chips user selected (0 = no filter)
- `seen_in_session`: count of times this dest appeared in this session's prior searches
- `cheapest_date_in_best_months`: bool, is the cheapest departure in dest.best_months?
- `novelty_score`: from destinations.novelty_score (1-5)

### Score formula

```python
def score(candidate, user_query, session):
    # budget_fit: reward the sweet spot, penalize too cheap and too expensive
    ratio = candidate.price_usd / user_query.budget_usd
    if 0.70 <= ratio <= 1.00:
        budget_fit = 1.0
    elif 0.50 <= ratio < 0.70:
        budget_fit = 0.6
    elif ratio < 0.50:
        budget_fit = 0.4  # suspiciously cheap, likely basic econ + bad times
    elif 1.00 < ratio <= 1.15:
        budget_fit = 0.5  # slightly over, shown if vibe match strong
    else:
        return None  # >15% over budget, filtered out of candidate set entirely

    # novelty: penalize repeats within session
    if session.seen_count[candidate.iata] == 0:
        novelty = 1.0
    elif session.seen_count[candidate.iata] == 1:
        novelty = 0.6
    else:
        novelty = 0.3

    # vibe_match: 0.5 baseline, +0.1 per overlap
    if user_query.vibe_count == 0:
        vibe_match = 1.0  # no filter
    else:
        vibe_match = 0.5 + (0.15 * candidate.vibe_overlap)
        vibe_match = min(vibe_match, 1.0)

    # seasonality
    seasonality = 1.0 if candidate.cheapest_date_in_best_months else 0.6

    # novelty_score (curator-rated): subtle boost for less-known places
    novelty_bonus = 1.0 + (candidate.novelty_score - 3) * 0.05
    # range: 0.90 (most cliche) to 1.10 (most novel)

    return budget_fit * novelty * vibe_match * seasonality * novelty_bonus
```

### Tie-breaking

- Higher novelty_score wins ties
- If still tied, lower price wins
- If still tied, alphabetical by city

### Return shape

Top 8 candidates returned. If fewer than 8 candidates pass `budget_fit > 0`, return what we have (minimum 1). If zero candidates, return empty list and frontend shows "Try a higher budget or different dates" message.

---

## 8. Card UX and catch voice

### Visual structure

```
┌─────────────────────────────────────────────┐
│ Mexico City, Mexico              $342      │
│ 7 nights · Feb 12-19                        │
│                                             │
│ catch: It's a city, not a beach.           │
│ February nights drop to 45°F. Locals       │
│ skip Reforma after 11pm.                    │
│                                             │
│ best months: Mar-May, Oct-Nov               │
│ daily budget: ~$60 food + lodging           │
│ vibes: city · food · history                │
│                                             │
│ See on Google Flights →                     │
└─────────────────────────────────────────────┘
```

**Note:** v1 cards do not show stop count or carrier (fli.SearchDates returns only date+price+currency). v1.1 will chain `fli.SearchFlights` against the top 8 ranked dates per request to enrich with stop count, carrier codes, and exact flight times. Users get the dates and the price; for booking-time details they click through to Google Flights.

### Catch composition

```python
def compose_catch(destination, route):
    parts = []
    if destination.base_catch:
        parts.append(destination.base_catch)
    if route and route.route_catch_text:
        parts.append(route.route_catch_text)
    return " ".join(parts) if parts else None
```

### Voice rules (for curation)

- Second-person, present tense ("you'll" not "travelers will")
- Specific facts over adjectives ("45°F" not "chilly")
- Lead with the catch, not a hedge ("It's a city, not a beach" not "While Mexico City is wonderful...")
- 1-3 sentences total, max ~200 chars combined
- No marketing copy. No "vibrant," "bustling," "hidden gem," "must-visit"
- Reference real local knowledge ("Reforma after 11pm")
- If no catch worth mentioning, leave base_catch null (rare for v1, expected for ~10% of destinations)

### Examples by tier

**Cliche destinations need stronger catches** (novelty_score 1-2):
- Bali: "Ubud is over-touristed. The cheap flights land you at DPS at 1am. Surfers swear by April."
- Cancun: "Spring break is March 1 to April 15. The all-inclusive resorts you see in ads aren't on the public beach."

**Novel destinations need context catches** (novelty_score 4-5):
- Tbilisi, Georgia: "Visa-free for 365 days. Wine and sulfur baths cost less than coffee in your city. Russian is more common than English."
- Yerevan, Armenia: "Five-hour layover in Istanbul or Doha is standard. Currency is dram, pulls in cash only outside Yerevan."

---

## 9. SEO pages (deferred to v1.1)

**Not in v1 scope.** SEO pages were considered and intentionally deferred after the tool-vs-SEO scope check on 2026-05-26.

The reasoning: the tool is the riskier assumption AND the unique positioning. Going.com and Skyscanner already have content arms; nobody owns the interactive "where can I take this budget" workflow. v1 ships the tool, proves people actually use it, then v1.1 layers SEO pages informed by what /go data tells us (which destinations resonate, which catches drive clicks, what queries people actually run).

Original v1 SEO design (1,380 pages across three URL patterns: `/from/<airport>/under/<budget>`, `/from/<airport>/<vibe>`, `/destination/<dest>/from/<airport>`) is preserved in git history (commit f85ff08, this same file pre-edit) for the v1.1 plan to reference.

---

## 10. Email gate

### Trigger condition

- Session has submitted >= 5 distinct `/api/go` searches (counted via `searches.session_id`)
- AND session has no associated row in `signups` joined via session cookie

### UX

- 6th submission: backend returns `{results: [...], email_gate_required: true}`
- Frontend renders modal overlay:

```
You're onto something.

We've shown you 47 trip ideas across 5 searches. Drop an email
and we'll send the next batch when prices shift on the ones
you've explored.

[email input] [Save my searches]

No spam. Unsubscribe one-click.
```

- Email submit → POST /api/signup (existing endpoint, sets `email_gate_satisfied=true` flag in session)
- "No thanks" link dismisses modal, blocks further searches in session
- Modal returns on next /go submit if dismissed

### Email follow-up

- Welcome email: immediate, listing the destinations explored in their last 5 searches with current prices
- Weekly digest: top price movers on their explored destinations
- (Welcome email content and digest design: deferred to post-launch refinement, not blocking v1)

---

## 11. Curation pipeline

### Authoring format: YAML in repo

Adam edits two files in `~/promptiv/data/`:

**airports.yaml** (12 entries, written once)
```yaml
- iata: BNA
  city: Nashville
  state: TN
  region_us: Southeast
  lat: 36.1245
  lng: -86.6782
  rank_us: 12

- iata: JFK
  city: New York
  state: NY
  region_us: Northeast
  lat: 40.6413
  lng: -73.7781
  rank_us: 1

# ... 10 more
```

**destinations.yaml** (100 entries, primary curation work)
```yaml
- iata: CDMX
  city: Mexico City
  country: Mexico
  country_code: MX
  region: Latin America
  vibes: [city, food, history]
  passport_required: true
  visa_required_us: false
  best_months: [3, 4, 5, 10, 11]
  avg_daily_cost_usd: 60
  safety_tier: 2
  currency: MXN
  lat: 19.4326
  lng: -99.1332
  novelty_score: 3
  base_catch: |
    It's a city, not a beach. February nights drop to 45°F.
    Locals skip Reforma after 11pm.

- iata: TBS
  city: Tbilisi
  country: Georgia
  country_code: GE
  region: Caucasus
  vibes: [city, food, history, off-grid]
  passport_required: true
  visa_required_us: false
  best_months: [5, 6, 9, 10]
  avg_daily_cost_usd: 35
  safety_tier: 1
  currency: GEL
  lat: 41.7151
  lng: 44.8271
  novelty_score: 5
  base_catch: |
    Visa-free for 365 days. Wine and sulfur baths cost less than
    coffee in your city. Russian is more common than English.

# ... 98 more
```

**routes.yaml** (~50 entries, route-specific catch overrides for high-surface routes only)
```yaml
- origin: BNA
  dest: NRT
  catch: |
    BNA->NRT always routes via DFW or LAX, plan 16h door-to-door.

- origin: BNA
  dest: CDG
  catch: |
    BNA->CDG cheap flights are JFK-CDG redeyes, expect 14h+ total.

# ... ~48 more
```

Targeted route_catch_text additions: pick the ~50 (origin, dest) pairs that most often surface as top-ranked /go results AND where the origin meaningfully changes the catch (long routings, layover patterns, season offsets). All other routes use only `destinations.base_catch`.

### Loader

`server/destinations.py` runs on every deploy and after every YAML edit:

```python
def load_yaml_into_db():
    """Idempotent: upserts airports, destinations, routes from YAML."""
    airports = yaml.safe_load(open("data/airports.yaml"))
    dests = yaml.safe_load(open("data/destinations.yaml"))
    routes = yaml.safe_load(open("data/routes.yaml"))

    with db.connect() as conn:
        upsert_airports(conn, airports)
        upsert_destinations(conn, dests)
        upsert_routes(conn, routes)
        # routes table also auto-populates: for every (airport, dest) pair
        # not in routes.yaml, insert a row with route_catch_text=null
        populate_missing_routes(conn)
```

### Curation workflow

1. Adam opens `data/destinations.yaml` in editor
2. Uses ChatGPT to draft structured fields for a batch (e.g., 20 destinations at a time): "Give me YAML entries for these 20 cities following this schema [paste]"
3. Reviews/edits the structured fields, hand-writes `base_catch` for each
4. Commits to git
5. Local: runs `python -m server.destinations` to load YAML → SQLite
6. Tests locally via `/go` and SEO pages
7. Pushes to production: rsync + `python -m server.destinations` on prod
8. Next nightly cron picks up new destinations and starts collecting prices

### Initial destination selection (100 destinations)

Suggested mix to draft during curation (not binding, adjustable):
- Latin America & Caribbean: 25 (closest, cheapest, no-passport options)
- Western Europe: 20 (highest demand, established routes)
- Eastern Europe & Caucasus: 12 (novelty plays, cheap on the ground)
- Asia: 18 (Japan, SE Asia, Korea)
- Middle East: 6 (Istanbul, Dubai, Amman, Tbilisi-adjacent)
- Africa: 8 (Morocco, Cape Town, Cairo, etc.)
- Oceania: 4
- US domestic: 7 (for under-$300 SEO traffic)

---

## 12. 3-week rollout plan

### Week 1 (May 27 - Jun 2)

**Backend:**
- Migrations for 5 new tables
- airports.yaml with 12 hubs
- destinations.yaml schema documented, first 30 destinations stubbed (structured fields only)
- `server/destinations.py` YAML loader (idempotent upsert)
- `server/fli_client.py` wrapper with mocked-for-testing mode
- `server/price_refresh.py` cron entry point + systemd unit (deployable but not enabled yet)
- **fli sanity spike** (early week 1, before anything else): hit fli with 1 origin × 5 real destinations × 3 trip lengths. Confirm reverse-engineering still works end-to-end. If broken, escalate before further investment.
- Tests: schema migration, YAML loader idempotency, fli_client mock responses

**Adam curation:**
- airports.yaml (12 entries, ~30 min)
- destinations.yaml structured fields for ~40 destinations (~4h with ChatGPT assist)

**Deliverable end of week 1:** schema in place, 40 destinations loaded, fli cron infrastructure tested with mocks, fli sanity spike confirmed.

### Week 2 (Jun 3 - Jun 9)

**Backend:**
- POST /api/go endpoint
- `server/ranking.py` with formula from §7
- `server/catch.py` compose logic
- fli cron goes live (first real production call to fli, ~3,600 calls/night)
- Tests: ranking edge cases, catch composition, /api/go integration

**Adam curation:**
- destinations.yaml structured fields for 40 more (running total: 80)
- Catch text for first 50 destinations (~8h)

**Frontend:**
- /go page: form (airport dropdown, budget input, trip-length 3-button, vibe chips) + results grid
- Card component (matches §8 visual)
- Inherits centered-editorial aesthetic from teaser (aurora, Instrument Serif, Inter)

**Deliverable end of week 2:** /go works end-to-end with 80 destinations, real cached prices, first 50 have catch text.

### Week 3 (Jun 10 - Jun 16)

**Backend:**
- Email gate logic (session counter + modal trigger)
- Quiet "notify me" CTA in /go footer (always visible, secondary acquisition path)
- Welcome email template via Resend
- E2E tests (Playwright) for /go flow + email gate
- Monitoring: /api/healthz extended with last_refresh_at, snapshot_count
- Production deploy: rsync, restart promptiv.service, enable systemd timer for nightly refresh

**Adam curation:**
- Final 20 destinations (running total: 100)
- Catch text for remaining 50 destinations (running total: 100)
- routes.yaml: ~50 high-surface route_catch_text overrides

**Frontend:**
- Email gate modal
- Mobile polish pass
- Landing page (existing teaser) updated to drive primary CTA to /go

**Deliverable end of week 3:** Promptiv v1 live on promptiv.io. All 100 destinations + catch text + email gate. Ship to sell.

### Launch day (Jun 16 or later)

- Run final fli refresh manually to ensure fresh prices
- Smoke test /go end-to-end on mobile and desktop
- Verify email gate triggers and welcome email sends
- Tweet/email launch announcement (Adam's network only — no broad marketing yet)
- Monitor /api/healthz, error logs, Resend deliverability, /go submission rate
- **Hold marketing push until tool data validates** (people use it more than once, share it, sign up at >25%)

---

## 13. Out of scope for v1

- **Programmatic SEO pages** (v1.1, see §9 for the deferred design)
- **Stop count and carrier display on cards** (v1.1: chain fli.SearchFlights on top ranked dates)
- User accounts, saved trips, trip boards (v1.1)
- Pro tier ($7/mo) (v1.1)
- Affiliate booking links (v1.1 if traffic justifies)
- Real-time price updates (v2)
- Hotels, cars, activities (never, focus is flights+vibe)
- Family/multi-passenger search (v2)
- TikTok/Reels content generation (v2)
- Admin UI (v1.1, curation via YAML+git for v1)
- Multi-language (English only at launch)
- Notifications other than the welcome email (v1.1)

---

## 14. Open questions (non-blocking)

1. **Sender domain.** Stay on `team@mail.distillworks.com` (current) or set up `team@promptiv.io`? Current works; promptiv.io looks more professional but requires Resend domain verification (~30 min, free). Decide before launch announcement.
2. **GDPR / privacy.** Currently a manual mailto for delete. If we get EU traffic, do we need a self-serve delete? Defer to first EU signup.
3. **Rate-limiting /api/go.** No rate limit in v1. If a scraper hits us, our fli cron will get blocked indirectly because /api/go doesn't call fli (it reads cache), so impact is limited. Add IP-based limit if abuse observed.
4. **Currency localization.** v1 shows USD only. Defer multi-currency to v2.
5. **What if fli is permanently broken before launch?** Contingency: pivot to SerpAPI's Google Flights endpoint (~$50/mo for v1 query volume) or Amadeus Self-Service (free tier limits unclear for our pattern). Spike during week 1: validate fli still works end-to-end with one origin/dest pair.

---

## 15. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| fli breaks during v1 build | Medium | High | Week 1 spike validates fli works. SerpAPI as backup ($50/mo). Architecture isolates fli to one module. |
| Google rate-limits fli at higher volume | Medium | High | 6s between calls. Cron runs once nightly. If blocked, prices go stale but app stays up. |
| Catch text quality varies | High | Medium | Hand-curated per destination. Voice guide in §8. Adam writes all of them (no delegation). |
| 3-week timeline slips | High | Low | Curation is the bottleneck. Can ship with 60-70 destinations and add the rest in weeks 4-5. /go still works at any destination count. |
| Tool gets low engagement on launch | Medium | High | This IS the validation signal. If <1 search per visitor average after 2 weeks, the tool hypothesis is wrong and we revisit before investing in SEO. |
| Email deliverability via Resend | Low | Medium | Resend already verified for distillworks.com. Welcome email tested. |
| Cron doesn't fire (systemd issue) | Low | Medium | Healthcheck monitors last_refresh_at. External uptime monitor (UptimeRobot free tier) pings /api/healthz. |
| Disk fills from price_snapshots | Low | Low | 14-day retention + monthly VACUUM. ~300MB steady state. |

---

## 16. Definition of done (v1)

- [ ] 100 destinations in destinations.yaml with structured fields
- [ ] 100 destinations with hand-written base_catch text
- [ ] 12 airports in airports.yaml
- [ ] ~50 route_catch_text overrides in routes.yaml (high-surface routes only)
- [ ] All 5 new SQLite tables created via migration
- [ ] fli sanity spike confirms reverse-engineering still works (week 1)
- [ ] fli cron runs nightly, completes in <8h, <5% failure rate
- [ ] /go workflow returns 5-8 cards in <500ms
- [ ] Email gate triggers at 6th search per session
- [ ] Always-visible secondary "notify me" CTA in /go footer
- [ ] Welcome email sends within 1 min of signup
- [ ] /api/healthz reports DB ok, last_refresh_at, snapshot count
- [ ] All E2E tests pass (Playwright)
- [ ] Mobile UX tested on actual phone
- [ ] Production deployed to promptiv.io
- [ ] Existing teaser landing page updated to drive primary CTA to /go
- [ ] Personal-network launch announcement sent (no broad marketing until tool data validates)

---

End of spec.
