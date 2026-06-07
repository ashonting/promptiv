"""Weekly per-city digest composer + sender (W4).

Built from the same engine the hubs use (server.hubs), so the digest and the
hub always agree. Three things keep it from going stale:

1. Trailing window: trips are ranked by the LAST 7 days' fares (build_hub
   `since=`), not the all-time floor, so "this week" actually moves week to week.
2. Rotating lens: each week leads with a different cut of the catalog
   (cheapest -> beach -> long-haul -> in-season -> food), chosen by ISO week.
3. Deal-alerts: a "just got cheaper" section that auto-appears per route once
   that route has enough history to call a price "below normal" (DEAL_MIN_OBS).
   Dormant until the archive deepens (~2 weeks), then lights up route by route.

The verified pairing stays the constant hero (the durable creative). Sending is
per-subscriber; failures are logged, never raised.
"""
import argparse
import datetime
import html
import logging
import os
import sqlite3
import statistics
import time
from typing import Optional

from server import hubs, email_client
from server.hubs import DISPLAY_NAMES
from server.hub_render import slugify

log = logging.getLogger(__name__)

BASE_URL = "https://dashaway.io"
TRAILING_DAYS = 7      # "this week" = fares observed in the last 7 days
N_FEATURE = 6          # trips in the week's lens section
N_REACH = 2            # trips in the recurring "farther than you think" section
N_DEALS = 3            # deal-alerts shown when eligible
SLEEP_BETWEEN_SENDS = 0.4  # gentle pacing under Resend's rate limit

# Deal-alert gate: only call a fare a "deal" when the route has real history.
DEAL_WINDOW_DAYS = 45  # how far back "normal" is measured
DEAL_RECENT_DAYS = 7   # what counts as "now"
DEAL_MIN_OBS = 14      # min distinct observation days before we trust "normal"
DEAL_MIN_DROP = 0.12   # >=12% under normal to surface

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# Each week leads with one of these (chosen by ISO week number). A lens that
# can't fill at least MIN_PICKS falls back to "cheapest".
MIN_PICKS = 3
LENSES = [
    {"key": "cheapest",  "subject": "This week's cheapest trips from {city}",
     "title": "This week's cheapest weeks", "note": "The lowest all-in totals from your city right now."},
    {"key": "beach",     "subject": "Beach weeks from {city}",
     "title": "Beach weeks worth the flight", "note": "Sun and sand, the whole week, for less than you'd guess."},
    {"key": "long_haul", "subject": "Farther than you think, from {city}",
     "title": "Farther than you think", "note": "Overseas weeks that still cost less than a domestic splurge."},
    {"key": "in_season", "subject": "Great in {month}: trips from {city}",
     "title": "In season right now", "note": "Destinations at their best in {month}."},
    {"key": "food",      "subject": "Where the food's worth the flight, from {city}",
     "title": "For the food", "note": "Cities where a week of great meals still comes in cheap."},
]

# Email palette — matches the welcome-email family.
CREAM = "#f5f3ee"; CARD = "#ffffff"; BORDER = "#ece9e1"
INK = "#1a1a1f"; BODY = "#3a3a42"; MUTE = "#8a8a92"; FAINT = "#5a5a62"; ACCENT = "#a78bfa"


def _esc(s) -> str:
    return html.escape(str(s))


def _money(n) -> str:
    return f"${int(n):,}"


def city_origin_iata(conn, city_name: str) -> Optional[str]:
    row = conn.execute("SELECT iata FROM airports WHERE city = ?", (city_name,)).fetchone()
    return row[0] if row else None


def pick_lens(as_of: datetime.date) -> dict:
    """Deterministic weekly lens from the ISO week number."""
    return LENSES[as_of.isocalendar()[1] % len(LENSES)]


def _lens_picks(lens_key: str, hub: dict, as_of: datetime.date, n: int = N_FEATURE) -> list:
    trips = hub["trips"]
    if lens_key == "beach":
        return [t for t in trips if "beach" in t["vibes"]][:n]
    if lens_key == "food":
        return [t for t in trips if "food" in t["vibes"]][:n]
    if lens_key == "in_season":
        return [t for t in trips if as_of.month in t["best_months"]][:n]
    if lens_key == "long_haul":
        hero = hub["hero"]
        bench = hero["anchor_total_usd"] if hero else (trips[-1]["total_usd"] if trips else 0)
        return [t for t in trips if t["overseas"] and t["total_usd"] < bench][:n]
    return trips[:n]  # cheapest


def detect_deals(conn, origin: str, as_of: datetime.date, nights: int = 7) -> list:
    """Routes whose recent fare is meaningfully under their own trailing normal.

    Gated: a route needs >= DEAL_MIN_OBS distinct observation days before we'll
    call anything "normal", so this returns [] until the archive is deep enough,
    then turns on route by route. Returns the biggest drops first.
    """
    window_start = (as_of - datetime.timedelta(days=DEAL_WINDOW_DAYS)).isoformat()
    recent_start = (as_of - datetime.timedelta(days=DEAL_RECENT_DAYS - 1)).isoformat()
    rows = conn.execute(
        "SELECT ph.dest_iata, ph.observed_date, ph.cheapest_price_usd, "
        "       d.city, d.country, d.avg_daily_cost_usd "
        "FROM price_history ph JOIN destinations d ON d.iata = ph.dest_iata "
        "WHERE ph.origin_iata = ? AND ph.trip_nights = ? "
        "AND ph.observed_date >= ? AND ph.observed_date <= ?",
        (origin, nights, window_start, as_of.isoformat()),
    ).fetchall()

    by_dest: dict = {}
    for dest, od, price, city, country, daily in rows:
        d = by_dest.setdefault(dest, {"city": city, "country": country, "daily": daily, "obs": []})
        d["obs"].append((od, price))

    deals = []
    for dest, info in by_dest.items():
        obs = info["obs"]
        if len({od for od, _ in obs}) < DEAL_MIN_OBS:
            continue
        baseline = statistics.median([p for _, p in obs])
        recent = [p for od, p in obs if od >= recent_start]
        if not recent or baseline <= 0:
            continue
        recent_min = min(recent)
        if recent_min <= baseline * (1 - DEAL_MIN_DROP):
            daily = int(info["daily"])
            deals.append({
                "iata": dest,
                "city": DISPLAY_NAMES.get(dest) or info["city"],
                "country": info["country"],
                "recent_total_usd": int(recent_min) + nights * daily,
                "baseline_total_usd": int(baseline) + nights * daily,
                "pct": round((baseline - recent_min) / baseline * 100),
            })
    deals.sort(key=lambda d: -d["pct"])
    return deals[:N_DEALS]


def compose_city_email(conn, city_name: str, as_of: Optional[datetime.date] = None,
                       week_index: Optional[int] = None, unsubscribe_url: str = "#",
                       base_url: str = BASE_URL) -> Optional[dict]:
    """Render the weekly email for one city. Returns {subject, html, text} or
    None if the city isn't served / has no recent trip data.

    `as_of` drives the trailing window, the in-season month, and the lens.
    `week_index` overrides the lens (for previewing different weeks).
    """
    if as_of is None:
        as_of = datetime.date.today()
    origin = city_origin_iata(conn, city_name)
    if not origin:
        return None

    window_start = (as_of - datetime.timedelta(days=TRAILING_DAYS - 1)).isoformat()
    hub = hubs.build_hub(conn, origin, since=window_start)
    if not hub["trips"]:  # thin window early on -> fall back to all-time
        hub = hubs.build_hub(conn, origin)
    if not hub["trips"]:
        return None

    hero = hub["hero"]
    lens = LENSES[week_index % len(LENSES)] if week_index is not None else pick_lens(as_of)
    feature = _lens_picks(lens["key"], hub, as_of)
    if len(feature) < MIN_PICKS:           # off-season / thin cut -> cheapest
        lens = LENSES[0]
        feature = _lens_picks("cheapest", hub, as_of)

    # Recurring signature section, unless the lens already is long-haul. Dedupe
    # against the feature so a city never appears twice in one email.
    reach = []
    if lens["key"] != "long_haul" and hero:
        seen = {f["iata"] for f in feature}
        candidates = hubs.long_haul_under(hub, hero["anchor_total_usd"], N_REACH + len(seen))
        reach = [t for t in candidates if t["iata"] not in seen][:N_REACH]

    deals = detect_deals(conn, origin, as_of)
    month = MONTHS[as_of.month - 1]
    subj = lens["subject"].format(city=city_name, month=month)
    hub_url = f"{base_url}/{slugify(city_name)}"

    return {
        "subject": subj,
        "html": _render_html(city_name, hero, lens, feature, reach, deals, month, hub_url, unsubscribe_url, base_url),
        "text": _render_text(city_name, hero, lens, feature, reach, deals, hub_url, unsubscribe_url),
    }


# ---------- rendering ----------

def _trip_rows_html(trips: list) -> str:
    out = []
    for t in trips:
        out.append(
            f'<tr><td style="padding:9px 0;border-bottom:1px solid {BORDER};color:{INK};font-size:15px;">'
            f'{_esc(t["city"])}<span style="color:{MUTE};font-size:13px;">, {_esc(t["country"])}</span></td>'
            f'<td align="right" style="padding:9px 0;border-bottom:1px solid {BORDER};'
            f'font-family:Georgia,serif;font-style:italic;color:{ACCENT};font-size:17px;white-space:nowrap;">'
            f'{_money(t["total_usd"])}</td></tr>'
        )
    return "".join(out)


def _section_html(title: str, note: str, rows_html: str) -> str:
    return (
        f'<p style="margin:30px 0 4px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;'
        f'color:{MUTE};font-weight:600;">{_esc(title)}</p>'
        f'<p style="margin:0 0 10px;color:{FAINT};font-size:13px;line-height:1.5;">{_esc(note)}</p>'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">{rows_html}</table>'
    )


def _deals_html(deals: list) -> str:
    if not deals:
        return ""
    rows = []
    for d in deals:
        rows.append(
            f'<tr><td style="padding:9px 0;border-bottom:1px solid {BORDER};color:{INK};font-size:15px;">'
            f'{_esc(d["city"])}<span style="color:{MUTE};font-size:13px;">, {_esc(d["country"])}</span>'
            f'<span style="display:block;color:{FAINT};font-size:12.5px;">{d["pct"]}% under its normal</span></td>'
            f'<td align="right" style="padding:9px 0;border-bottom:1px solid {BORDER};'
            f'font-family:Georgia,serif;font-style:italic;color:{ACCENT};font-size:17px;white-space:nowrap;">'
            f'{_money(d["recent_total_usd"])}</td></tr>'
        )
    return _section_html("Just got cheaper", "Below their usual price from your city this week.", "".join(rows))


def _render_html(city, hero, lens, feature, reach, deals, month, hub_url, unsub_url, base_url) -> str:
    hero_block = ""
    if hero:
        hero_block = (
            f'<p style="margin:16px 0 6px;font-family:Georgia,\'Times New Roman\',serif;font-style:italic;'
            f'font-size:23px;color:{INK};line-height:1.25;">'
            f'A week in {_esc(hero["cheap_city"])} costs less than a week in {_esc(hero["anchor_city"])}.</p>'
        )
    reach_block = ""
    if reach:
        reach_block = _section_html(
            "Farther than you think",
            f'Overseas weeks under a week in {hero["anchor_city"]}.' if hero else "Overseas weeks worth the distance.",
            _trip_rows_html(reach),
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width,initial-scale=1.0" />
<title>{_esc(lens["subject"].format(city=city, month=month))}</title>
</head>
<body style="margin:0;padding:0;background:{CREAM};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:{CREAM};">
    <tr><td align="center" style="padding:40px 16px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:560px;background:{CARD};border-radius:14px;border:1px solid {BORDER};">
        <tr><td style="padding:34px 36px 4px 36px;">
          <div style="font-family:Georgia,'Times New Roman',serif;font-size:23px;font-weight:400;color:{INK};letter-spacing:-0.01em;">
            DashAway<span style="display:inline-block;width:6px;height:6px;background:{ACCENT};border-radius:50%;margin-left:5px;vertical-align:middle;transform:translateY(-6px);"></span>
          </div>
          <p style="margin:14px 0 0;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:{MUTE};font-weight:600;">Cheap trips from {_esc(city)}</p>
        </td></tr>
        <tr><td style="padding:4px 36px 30px 36px;color:{BODY};font-size:15px;line-height:1.6;">
          {hero_block}
          <p style="margin:6px 0 0;color:{FAINT};font-size:13.5px;line-height:1.55;">Ranked by what the whole week actually costs, airfare plus a week on the ground.</p>
          {_deals_html(deals)}
          {_section_html(lens["title"], lens["note"].format(month=month), _trip_rows_html(feature))}
          {reach_block}
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:30px 0 8px;">
            <tr><td bgcolor="{ACCENT}" style="border-radius:10px;">
              <a href="{_esc(hub_url)}" style="display:inline-block;padding:13px 26px;color:#0a0a0e;text-decoration:none;font-weight:600;font-size:14.5px;letter-spacing:0.01em;">See all {_esc(city)} trips &rarr;</a>
            </td></tr>
          </table>
          <p style="margin:18px 0 0;color:{INK};font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:15px;">&mdash; Adam</p>
        </td></tr>
        <tr><td style="padding:18px 36px;border-top:1px solid {BORDER};color:{MUTE};font-size:11.5px;line-height:1.6;">
          You're getting this because you asked for {_esc(city)}'s cheapest trips.
          <a href="{_esc(unsub_url)}" style="color:{MUTE};text-decoration:underline;">Unsubscribe</a>.<br />
          &copy; 2026 DashAway &middot; <a href="{_esc(base_url)}/privacy" style="color:{MUTE};text-decoration:underline;">Privacy</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def _render_text(city, hero, lens, feature, reach, deals, hub_url, unsub_url) -> str:
    lines = [lens["subject"].format(city=city, month=MONTHS[datetime.date.today().month - 1]), ""]
    if hero:
        lines += [f"A week in {hero['cheap_city']} costs less than a week in {hero['anchor_city']}.", ""]
    if deals:
        lines.append("JUST GOT CHEAPER (below their usual from your city)")
        for d in deals:
            lines.append(f"  {d['city']}, {d['country']} — {_money(d['recent_total_usd'])} ({d['pct']}% under normal)")
        lines.append("")
    lines.append(lens["title"].upper())
    for t in feature:
        lines.append(f"  {t['city']}, {t['country']} — {_money(t['total_usd'])}")
    if reach:
        lines += ["", "FARTHER THAN YOU THINK"]
        for t in reach:
            lines.append(f"  {t['city']}, {t['country']} — {_money(t['total_usd'])}")
    lines += ["", f"See all {city} trips: {hub_url}", "", "— Adam", "", f"Unsubscribe: {unsub_url}"]
    return "\n".join(lines) + "\n"


# ---------- sending ----------

# Each subscriber has a unique unsubscribe link, but a city's email content is
# identical, so compose once per city with this placeholder and swap it in per
# subscriber (cheap string replace) instead of re-running the engine each time.
UNSUB_SENTINEL = "%%UNSUB_URL%%"


def send_digest(conn, as_of: Optional[datetime.date] = None, dry_run: bool = True,
                base_url: str = BASE_URL, sleep: float = SLEEP_BETWEEN_SENDS) -> dict:
    """Compose each subscriber's city email (cached per city) and send it with
    their own unsubscribe link. dry_run=True (default) composes + counts but
    sends nothing. Returns a summary dict."""
    if as_of is None:
        as_of = datetime.date.today()
    subs = conn.execute(
        "SELECT email, digest_city, unsub_token FROM signups "
        "WHERE unsubscribed_at IS NULL AND digest_city IS NOT NULL AND digest_city != '' "
        "ORDER BY digest_city, email"
    ).fetchall()

    cache: dict = {}
    summary = {"subscribers": len(subs), "would_send": 0, "skipped_no_content": 0,
               "by_city": {}, "dry_run": dry_run}
    for email_addr, city, token in subs:
        if city not in cache:
            cache[city] = compose_city_email(
                conn, city, as_of=as_of, unsubscribe_url=UNSUB_SENTINEL, base_url=base_url)
        composed = cache[city]
        if composed is None:
            summary["skipped_no_content"] += 1
            continue
        unsub_url = f"{base_url}/unsubscribe?token={token}"
        html_body = composed["html"].replace(UNSUB_SENTINEL, unsub_url)
        text_body = composed["text"].replace(UNSUB_SENTINEL, unsub_url)
        if not dry_run:
            email_client.send_digest_email(
                email_addr, composed["subject"], html_body, text_body, unsubscribe_url=unsub_url)
            if sleep:
                time.sleep(sleep)
        summary["would_send"] += 1
        summary["by_city"][city] = summary["by_city"].get(city, 0) + 1
    return summary


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Send the weekly per-city digest.")
    ap.add_argument("--send", action="store_true",
                    help="actually send (default is a dry run that sends nothing)")
    ap.add_argument("--as-of", help="ISO date override for the trailing window / lens (default: today)")
    args = ap.parse_args()

    db_path = os.environ.get("DATABASE_PATH", "/var/lib/promptiv/teaser.sqlite")
    as_of = datetime.date.fromisoformat(args.as_of) if args.as_of else datetime.date.today()
    conn = sqlite3.connect(db_path)
    try:
        summary = send_digest(conn, as_of=as_of, dry_run=not args.send)
    finally:
        conn.close()
    log.info("digest %s: %s", "SENT" if args.send else "DRY-RUN", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
