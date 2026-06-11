# r/dataisbeautiful submission

## Posting mechanics
- Post the HERO chart (`cheap_flight_trap.png`) as the single image. Striking single images outperform galleries here.
- Upload `trap_holds_everywhere.png` to imgur first; drop its link in your own OC source comment (and re-drop it whenever someone says "you cherry-picked the origin").
- Title MUST be descriptive (not editorialized) and tagged [OC]. Post the source comment within a few minutes of submitting — it's required, and it's where the link lives.
- Flair: OC.

## Title options (pick one — all descriptive, [OC])
1. [OC] Airfare vs. the all-in cost of a week of travel, for 96 destinations from Atlanta
2. [OC] The cheapest flight is rarely the cheapest trip — airfare vs. all-in weekly cost, 96 destinations from Atlanta
3. [OC] Round-trip airfare explains only a third of what a week of travel actually costs (96 destinations)

Recommended: #2 (states the finding without clickbait phrasing).

## Required OC source comment (post immediately after)

Source: round-trip airfares pulled live from Google Flights (cheapest 7-night round trip, departing ~2 weeks out), combined with a per-destination daily on-ground cost estimate (lodging + food + local transport, one person, mid-range). Each dot is one destination — all 96 priced from Atlanta (ATL) on the same day, 2026-06-08. All-in = airfare + 7 × daily cost. Color is the daily ground cost, which is the hidden variable doing most of the work.

Tools: Python + matplotlib.

Two honest caveats: the daily costs are directional estimates, not bookable quotes, and "cheapest flight" is the cheapest fare on that one day (fares move). The ranking is the point, not any single dollar figure.

The flip isn't an Atlanta quirk. A week in Guatemala City beats a week in Orlando from all 12 US origins I price — and Orlando is the cheaper flight every single time: https://imgur.com/a/gKBnDnv

I built a tool that does this pricing daily (airfare + ground cost, all-in, for a bunch of US cities) at dashaway.io if you want to poke at the underlying data.

## Engagement plan (this is what makes it work)
- Be at the keyboard for the first 1-2 hours. Reply to every early comment.
- Expect: "your ground-cost numbers are made up" → agree they're estimates, explain the source, point out the ranking is robust to the exact figures.
- Expect: "Orlando at $150/day is high" → fair, US domestic is pricey; the relative gap is what matters.
- Keep the tool mention low-key. The chart is the star; the link is a footnote.
