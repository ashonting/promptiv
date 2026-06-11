# DashAway — Destination Expansion Analysis (+25 candidates)

**Status:** PAUSED for revisit (saved 2026-06-10). Analysis + recommended slate done; nothing implemented. Decision pending.

**Goal:** add ~25 destinations (current set = 100). User settled on 25 as the right number after weighing the implications below.

---

## Implications of expanding (why 25, not 50)

The nightly refresh (`server/price_refresh.py`) is **sequential + deliberately rate-limited** (`time.sleep` between requests, no parallelism), so runtime scales **linearly with route count**.

- Current: 12 origins × 100 dests = **1,200 routes**, ~**5.5h** (07:00 → ~12:30 UTC). Regen runs **14:00 UTC** (≈1.5h buffer).
- +25 dests → 1,500 routes → ~6.9h → finishes ~13:55 (≈5 min before regen — too tight).
- +50 dests → 1,788 routes → ~8.25h → finishes ~15:15 (collides with regen → regenerates on partial data).

**Binding constraints / risks:**
1. **Timing:** must shift `promptiv-regen.timer` later (e.g. 17:00 UTC) and/or `promptiv-refresh.timer` earlier (05:00). 2-line systemd change, but required even at +25.
2. **Rate-limit / blocking risk** (the real technical risk): more Google Flights requests = higher throttle/block odds. Watch first 3-4 runs after expansion.
3. **Curation quality = the actual moat risk** (not technical): each new dest needs a defensible `avg_daily_cost_usd` (the number the whole "cheap flight is a trap" thesis rests on) + region/country/vibes/safety_tier/best_months/currency.
4. **Storage:** slow-burn only. DB 163MB, 13GB free; `fare_observations` grows ~96K→~120K rows/day. Eventually wants a retention/rollup policy. Not a blocker.
5. **Memory & $:** non-issues. Sequential refresh = low RAM (won't OOM the 1GB droplet); fli scrapes Google for free ($0 incremental API cost).

---

## Current distribution (100 dests)

| Region | Count | Read |
|---|---|---|
| Western Europe | 20 | OVER-indexed — do not add more |
| Asia | 18 | Well covered |
| Latin America | 16 | Good, some holes |
| Eastern Europe | 10 | Solid |
| Caribbean | 9 | UNDER-weight for a US product |
| Africa | 8 | Demand-appropriate |
| North America | 7 (all US) | STRUCTURALLY broken (no Canada) |
| Middle East | 6 | Fine |
| Oceania | 4 | Far/expensive, fine |
| Caucasus | 2 | Niche, fine |

## The three structural gaps
1. **Canada is 0 of 100** — biggest hole for a US-origin product. Vancouver/Montréal/Toronto are top-demand, cheap close flights, passport-easy, distinct.
2. **Caribbean under-built + missing its highest-demand islands** — no Turks & Caicos, Grand Cayman, St. Lucia, Curaçao (the most-searched US-Caribbean spots).
3. **Western Europe saturated (20)** — any new "Europe" slots go to cheap-ground east (Balkans/Baltics), where the moat lives.

## Secondary gaps
- Demand holes inside covered regions: **Tulum** (have Cancún/PV, not Tulum), **New Orleans**, **Antigua Guatemala** (listed the capital, not the gem), **Santorini** (only Athens for Greece).
- South America map holes: no Ecuador (Quito), Chile (Santiago), Belize. (Cusco covers Peru/Machu Picchu.)
- Whole regions absent: Central Asia (Samarkand/Tashkent), South Pacific beyond Fiji (Tahiti).
- Vibe gaps: nature/adventure + ski thin (Jackson Hole is the only mountain town).
- Cost-tier: cheap-ground bench (<$50/day, ~17 dests) is the moat — extend it into new regions.

---

## Recommended 25 (mix: ~60% high-demand fill, ~40% cheap-ground moat)

**$/day are starting ESTIMATES — must be curated/verified before adding.**

| # | Destination | ~$/day | Vibe | Gap it fills |
|---|---|---|---|---|
| 1 | Vancouver, Canada | 140 | city/nature | Canada (none) + PNW |
| 2 | Montréal, Canada | 110 | food/city/history | Canada |
| 3 | Toronto, Canada | 130 | city | Canada |
| 4 | Banff/Calgary, Canada | 150 | nature | Canada + mountain/outdoors |
| 5 | Turks & Caicos (PLS) | 250 | beach | top Caribbean demand |
| 6 | Grand Cayman (GCM) | 220 | beach | top Caribbean demand |
| 7 | St. Lucia (UVF) | 180 | beach/nature | Caribbean |
| 8 | Curaçao (CUR) | 140 | beach | Caribbean (ABC) |
| 9 | Tulum, Mexico | 120 | beach/wellness | #1 missing Mexico search |
| 10 | Antigua, Guatemala | 50 | history | the gem vs the capital; cheap-ground |
| 11 | Belize / San Pedro (BZE) | 120 | beach/nature | Central America, English-speaking |
| 12 | Quito, Ecuador | 45 | history/nature | Ecuador (none); cheap-ground |
| 13 | Santiago, Chile | 70 | city/gateway | Chile (none) |
| 14 | Mendoza, Argentina | 60 | wine/nature | wine/nature vibe |
| 15 | New Orleans, USA | 120 | food/nightlife/history | top US cultural trip |
| 16 | Siem Reap, Cambodia | 35 | Angkor/history | ultra cheap-ground moat |
| 17 | Colombo–Galle, Sri Lanka | 45 | beach/nature | rising, cheap-ground |
| 18 | Da Nang, Vietnam | 45 | beach | adds coast to Vietnam pair |
| 19 | Bucharest, Romania | 50 | city/history | cheap-ground east |
| 20 | Tallinn, Estonia | 60 | history | fills the Baltics |
| 21 | Kotor, Montenegro | 60 | beach/nature | Adriatic, cheap-ground |
| 22 | Santorini, Greece | 160 | beach | iconic Greek island demand |
| 23 | Samarkand/Tashkent, Uzbekistan | 40 | Silk Road | opens Central Asia |
| 24 | Accra, Ghana | 70 | city/food | West Africa / diaspora |
| 25 | Papeete, Tahiti | 200 | beach/nature | South Pacific bucket-list |

**Strategic split:**
- **Demand/SEO drivers** (Canada, Turks, Grand Cayman, Tulum, New Orleans, Santorini): high search volume, fill obvious holes, drive traffic. These lean into the "cheap flight is a trap" narrative (expensive ground).
- **Moat/inversion** (Quito, Antigua, Siem Reap, Samarkand, Bucharest, Kotor, Colombo): cheap-ground bargains that deepen "your money goes farther" and create new flips.

---

## When revisiting — next steps
1. User approves / swaps / cuts the slate.
2. **Real work:** research + lock curated metadata per dest (esp. `avg_daily_cost_usd`).
3. Add to the `destinations` table (+ region/country/vibes/safety_tier/best_months/currency/novelty/lat-lng/passport-visa).
4. **Shift `promptiv-regen.timer` later** before the first expanded refresh run.
5. Watch first 3-4 nightly runs for runtime creep + Google throttling.
6. Verify hubs/budget/comparison pages pick up the new dests (selectivity gates still apply — enrich existing pages, don't spawn thin ones).
