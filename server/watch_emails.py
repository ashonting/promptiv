"""Compose watch alert + pulse + confirm emails (DashAway email palette).

All HTML inline (no stylesheets), matching server/digest.py conventions.
Honesty rules: observed history only; always 'prices move, verify before booking'.
"""
from datetime import datetime
from urllib.parse import quote

CREAM = "#f5f3ee"; CARD = "#ffffff"; BORDER = "#ece9e1"
INK = "#1a1a1f"; BODY = "#3a3a42"; MUTE = "#8a8a92"; ACCENT = "#a78bfa"
GREEN = "#0f7d64"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"


def _fmt_date(iso):
    return datetime.fromisoformat(iso).strftime("%b %-d")


def _dest_name(conn, iata):
    row = conn.execute(
        "SELECT city, country, avg_daily_cost_usd FROM destinations WHERE iata=?",
        (iata,)).fetchone()
    if row:
        return row[0], row[1], row[2]
    return iata, None, None


def gf_link(origin, dest, depart, ret):
    q = f"Flights from {origin} to {dest} on {depart} through {ret}"
    return "https://www.google.com/travel/flights?q=" + quote(q)


def compose_alert(conn, watch, decision, best, base_url):
    price, dep, ret = best
    city, country, daily = _dest_name(conn, watch["dest_iata"])
    place = country if (country and "Turks" in country) else city
    manage = f"{base_url}/watch/manage?token={watch['manage_token']}"
    week = f"{_fmt_date(dep)}–{_fmt_date(ret)}"
    subject = f"↓ ${price:,.0f} — your {place} trip ({week})"

    receipts = []
    n = decision.get("nights_watched") or 0
    if n >= 2:
        receipts.append(f"lowest we've seen in {n} nights of watching"
                        if decision["trigger"] == "drop"
                        else f"{n} nights of watching")
    if decision.get("percentile") is not None:
        receipts.append(
            f"bottom {max(decision['percentile'], 1):.0f}% of everything we've observed")
    receipt_line = " · ".join(receipts)

    allin = ""
    if daily:
        total = price + watch["trip_nights"] * daily
        allin = (f'<p style="margin:14px 0 0;font:14px {SANS};color:{BODY}">'
                 f'${price:,.0f} flight → about <b>${total:,.0f} all-in</b> for '
                 f'the {watch["trip_nights"]}-night trip '
                 f'(flight + ~${daily}/day on the ground).</p>')

    link = gf_link(watch["origin_iata"], watch["dest_iata"], dep, ret)
    html = f"""<!doctype html><html><body style="margin:0;background:{CREAM};padding:24px 12px">
<div style="max-width:560px;margin:0 auto;background:{CARD};border:1px solid {BORDER};border-radius:12px;padding:28px">
  <p style="margin:0;font:600 11px {SANS};letter-spacing:.08em;color:{ACCENT}">DASHAWAY WATCH</p>
  <p style="margin:14px 0 0;font:italic 30px {SERIF};color:{INK}">${price:,.0f} to {city}.</p>
  <p style="margin:6px 0 0;font:15px {SANS};color:{BODY}">
    {watch['origin_iata']} → {watch['dest_iata']} · <b>{week}</b> · {watch['trip_nights']} nights</p>
  {f'<p style="margin:10px 0 0;font:13.5px {SANS};color:{GREEN}"><b>{receipt_line}</b></p>' if receipt_line else ''}
  {allin}
  <p style="margin:22px 0 0"><a href="{link}"
     style="display:inline-block;background:{ACCENT};color:#fff;text-decoration:none;font:600 15px {SANS};padding:12px 22px;border-radius:8px">
     See it on Google Flights</a></p>
  <p style="margin:18px 0 0;font:12px {SANS};color:{MUTE}">Prices move — verify before booking.
     We report what we observed; we never predict.</p>
  <p style="margin:16px 0 0;font:12px {SANS};color:{MUTE}">
     <a href="{manage}" style="color:{MUTE}">Pause or manage this watch</a></p>
</div></body></html>"""

    text = (f"${price:,.0f} — {watch['origin_iata']} to {watch['dest_iata']}, {week}, "
            f"{watch['trip_nights']} nights.\n"
            + (receipt_line + "\n" if receipt_line else "")
            + f"See it: {link}\nPrices move - verify before booking.\nManage: {manage}\n")
    return {"subject": subject, "html": html, "text": text}


def compose_pulse(rows, base_url):
    """rows: watch dicts each with _best=(price,dep,ret)|None, _nights, _trend."""
    items = []
    for w in rows:
        manage = f"{base_url}/watch/manage?token={w['manage_token']}"
        if w.get("_best") and w["_best"][0] is not None:
            p, dep, ret = w["_best"]
            arrow = {"down": "↓", "up": "↑"}.get(w.get("_trend"), "→")
            line = (f"best week {_fmt_date(dep)}–{_fmt_date(ret)} at "
                    f"<b>${p:,.0f}</b> · trending {arrow}")
        else:
            line = "no fares observed this week"
        items.append(
            f'<div style="padding:14px 0;border-bottom:1px solid {BORDER}">'
            f'<p style="margin:0;font:600 15px {SANS};color:{INK}">'
            f'{w["origin_iata"]} → {w["dest_iata"]}</p>'
            f'<p style="margin:4px 0 0;font:13.5px {SANS};color:{BODY}">'
            f'Watched {w.get("_nights", 0)} nights · {line}</p>'
            f'<p style="margin:4px 0 0;font:12px {SANS}">'
            f'<a href="{manage}" style="color:{MUTE}">manage</a></p></div>')
    html = f"""<!doctype html><html><body style="margin:0;background:{CREAM};padding:24px 12px">
<div style="max-width:560px;margin:0 auto;background:{CARD};border:1px solid {BORDER};border-radius:12px;padding:28px">
  <p style="margin:0;font:600 11px {SANS};letter-spacing:.08em;color:{ACCENT}">DASHAWAY WATCH · WEEKLY PULSE</p>
  <p style="margin:12px 0 8px;font:italic 24px {SERIF};color:{INK}">Still watching.</p>
  {''.join(items)}
  <p style="margin:18px 0 0;font:12px {SANS};color:{MUTE}">We email alerts only when something is decision-worthy. Prices move — verify before booking.</p>
</div></body></html>"""
    text = "\n".join(
        f"{w['origin_iata']}->{w['dest_iata']}: watched {w.get('_nights', 0)} nights"
        for w in rows)
    return {"subject": "Your watches · weekly pulse", "html": html, "text": text}


def send_watch_confirm(email, watch, confirm_url):
    """Double opt-in: watch is pending until this link is clicked."""
    from server import email_client
    html = f"""<!doctype html><html><body style="margin:0;background:{CREAM};padding:24px 12px">
<div style="max-width:560px;margin:0 auto;background:{CARD};border:1px solid {BORDER};border-radius:12px;padding:28px">
  <p style="margin:0;font:600 11px {SANS};letter-spacing:.08em;color:{ACCENT}">DASHAWAY WATCH</p>
  <p style="margin:12px 0 0;font:italic 26px {SERIF};color:{INK}">Confirm your watch.</p>
  <p style="margin:10px 0 0;font:15px {SANS};color:{BODY}">
    {watch['origin_iata']} → {watch['dest_iata']} ·
    {_fmt_date(watch['window_start'])} – {_fmt_date(watch['window_end'])} ·
    {watch['trip_nights']} nights</p>
  <p style="margin:20px 0 0"><a href="{confirm_url}"
     style="display:inline-block;background:{ACCENT};color:#fff;text-decoration:none;font:600 15px {SANS};padding:12px 22px;border-radius:8px">
     Start watching</a></p>
  <p style="margin:16px 0 0;font:12px {SANS};color:{MUTE}">We'll check it every night and
     email only when something is decision-worthy. If you didn't request this, ignore it.</p>
</div></body></html>"""
    text = (f"Confirm your DashAway watch: {watch['origin_iata']} -> "
            f"{watch['dest_iata']}, {watch['window_start']} to "
            f"{watch['window_end']}, {watch['trip_nights']} nights.\n"
            f"Confirm: {confirm_url}\nIf you didn't request this, ignore it.\n")
    return email_client.send_digest_email(
        email, "Confirm your DashAway watch", html, text)
