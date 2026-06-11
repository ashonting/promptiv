# Promptiv Teaser Page — Design Spec

**Date:** 2026-05-25
**Author:** Adam (with Claude Code, superpowers:brainstorming)
**Status:** Design approved, awaiting user review before implementation plan
**Replaces:** the existing placeholder page at promptiv.io
**Product brief:** `~/dashaway/PRODUCT-BRIEF.md`

---

## 1. Purpose

Replace the current promptiv.io placeholder with a teaser that **validates demand for the Promptiv Trips product** before any product is built. The product itself is idea-stage; this teaser is the first public artifact.

The teaser is a single page at promptiv.io. It collects emails and optional qualifier data. Both signup volume and qualifier responses become signal for the build/no-build decision and the eventual MVP scope.

## 2. Goals and success criteria

**Primary goal:** measure whether the Promptiv hook ("Find the trip hiding in your budget") attracts signups from real visitors, and learn what kind of traveler responds.

**Success signals to capture:**
1. Email-only signup conversion rate (visitor → signup) — measures hook strength
2. Qualifier-fill rate (signup → completed optional fields) — measures intent depth
3. Budget-bucket distribution (Under $500 / $500–1,200 / >$1,200) — tells which Promptiv Score categories matter to early users
4. Home airport distribution — geographic targeting signal
5. Open-text "biggest travel frustration" responses — qualitative gold for future copy and product scoping

**Explicitly not goals:**
- Brand awareness building (idea-stage, no marketing spend planned)
- Search ranking optimization (a teaser isn't an SEO play)
- Lead nurture or revenue (defer until product is built)

## 3. User flow

```
                                ┌───────────────────────────┐
                                │   Visitor lands at        │
                                │   promptiv.io             │
                                └────────────┬──────────────┘
                                             │
                                             ▼
                  ┌──────────────────────────────────────────────────┐
                  │  Sees:                                            │
                  │    Headline + subhead                             │
                  │    Rotating example trip card (5 cycles, 6s each) │
                  │    Email field + "Where can I go?" button         │
                  └────────────────────────┬─────────────────────────┘
                                           │
                                           │ visitor enters email + submits
                                           ▼
                  ┌──────────────────────────────────────────────────┐
                  │  Cards keep rotating above.                       │
                  │  Form area transitions to:                        │
                  │    "We're working on it."                         │
                  │    + 3 optional qualifiers                        │
                  │      - Budget intuition (3 buttons, mid-default)  │
                  │      - Home airport (text, optional)              │
                  │      - Biggest frustration (textarea, optional)   │
                  │    Actions: "Share" / "No thanks"                 │
                  └────────────────────────┬─────────────────────────┘
                                           │
                                           ▼
                  ┌──────────────────────────────────────────────────┐
                  │  Confirmation email sent via Resend.              │
                  │  Subscriber row + qualifiers persisted to SQLite. │
                  └──────────────────────────────────────────────────┘
```

There is only one page. There is no logged-in experience. There is no working product behind the form yet (and the design must never imply otherwise).

## 4. Visual design

### Color

| Token | Value | Use |
|---|---|---|
| `--color-bg` | `#0a0814` | Page background — near-black, tinted toward the accent |
| `--color-accent` | `#a78bfa` | Brand accent (locked, carried over from the current placeholder) |
| `--color-text-primary` | `#ffffff` | Headline, "You're on the list" / "We're working on it", city names in cards |
| `--color-text-secondary` | `#d8d4f0` / `#c8c2e4` | Body text in qualifiers |
| `--color-text-tertiary` | `#8b85b8` | Subhead, qualifier labels |
| `--color-text-quaternary` | `#7a749e` | Card meta, "No thanks" link |
| `--color-text-quinary` | `#5a557a` | "(optional)" hints |
| `--color-text-faint` | `#4a4670` | Footer |
| `--color-border` | `#2e2a48` | Form inputs, pill buttons |
| `--color-card-bg` | `rgba(167, 139, 250, 0.05)` | Example card background |
| `--color-card-border` | `rgba(167, 139, 250, 0.16)` | Example card border |

### Typography

- **Family:** General Sans (Pangram Pangram, via Fontshare CDN initially, self-host before launch)
- **Weights to load:** 400, 500, 600, and italic 400
- **Scale:**
  - Headline: 36px / 500 / -0.025em letter-spacing / 1.08 line-height
  - Subhead: 15px / 400 / 1.55 line-height
  - Card city: 15px / 600
  - Card meta: 12.5px / 400
  - Card catch: 12.5px / italic 400
  - Form input: 13.5px / 400
  - Button: 13.5px / 600
  - Acknowledgment: 16px / 500
  - Qualifier label: 13.5px / 500
  - Pill button: 13px / 400
  - Footer: 10.5px / 400

### Layout

- Single centered column, max-width 540px
- Padding: 56px top, 36px sides, 40px bottom (mobile pads down to ~24px sides)
- 84px gap between top of page and headline (where the wordmark used to be)
- 36px gap between subhead and card stack
- 36px gap between card stack and form
- 24px gap between form and footer

### Wordmark

**None.** The headline carries identity. The browser tab title and URL do the rest of the work.

### Footer

- Single line, very muted (`--color-text-faint`)
- Content: `© 2026 Promptiv · Privacy · Terms`
- "Privacy" and "Terms" are underlined links (underline color: `#2e2a48`)

## 5. Copy (locked)

```
Headline:    Somewhere new is closer than you think.
             (italic on "closer", colored with --color-accent)

Subhead:     Your budget is bigger than your map.

Example cards (rotating; see section 6 for full set)

Form CTA:    Where can I go?

After submit:
  Ack:       We're working on it.
  Lead-in:   Two quick optionals — they'll shape what we build first.
  Q1 label:  When you think about a trip, you're usually working with:
             Buttons: Under $500 | $500 – 1,200 | More than $1,200
             (Mid-bucket pre-selected as default)
  Q2 label:  Home airport (optional)
             Placeholder: BNA, LAX, JFK…
  Q3 label:  What's the worst part about planning a trip right now? (optional)
             Placeholder: A sentence or two. We read these.
  Actions:   [Share] | No thanks
```

## 6. Example trip cards (locked)

Five cards rotate in this order:

| # | City | Cost | Trip | Catch |
|---|---|---|---|---|
| 1 | San Juan, Puerto Rico | $342 | 4 nights · 1 stop · no passport | return lands at 11:40pm |
| 2 | Lisbon, Portugal | $612 | 7 nights · 1 stop | 13-hour door to door |
| 3 | Mexico City | $298 | 5 nights · nonstop | it's a city, not a beach |
| 4 | Reykjavik, Iceland | $789 | 6 nights · 1 stop | 5 hours of daylight in November |
| 5 | Tokyo, Japan | $1,287 | 10 nights · 1 stop | prices jump 40% during cherry blossom season |

Order rationale: budget → mid → budget → adventure → stretch. Sequence shows price range without telegraphing a single tier.

Prices are illustrative — they don't have to be live-accurate. If anyone notices they're stale, that's fine. The teaser doesn't promise these specific deals.

## 7. Motion and animation

**Library:** GSAP 3.x (CDN at first, self-host before launch).

**Card rotation:**
- 5 cards stacked absolutely in a fixed-height container (116px)
- One card visible at a time
- Dwell: 6 seconds per card
- Crossfade: 1.2 seconds, ease `power4.out` (ease-out-quart)
- Animated properties: `opacity` and `translateY` only (compositor-friendly; no layout thrash)
- 50% overlap between out-tween and in-tween (true crossfade, not flash)
- `will-change: opacity, transform` set on cards

**No other animation** on the page. No hover scale effects, no form-field transitions beyond color, no scroll animation. The card rotation is the only motion.

**Reduced motion:**
- `@media (prefers-reduced-motion: reduce)` query disables the rotation
- Only the first card (San Juan) renders, statically
- GSAP is still loaded but not invoked

**Fallback if GSAP fails to load:**
- First card shows statically
- No rotation, no error
- Visitor sees a coherent (if static) page

## 8. Accessibility

- All interactive elements reachable via keyboard
- Visible focus state on form inputs and buttons (browser default + accent color outline)
- Color contrast: headline white on `#0a0814` = ~16:1 (WCAG AAA); subhead `#8b85b8` on `#0a0814` = ~6.3:1 (WCAG AA)
- `prefers-reduced-motion` honored (see section 7)
- Form input has visible label via placeholder; sighted-only — needs proper `<label>` on implementation
- Submit button has descriptive text ("Where can I go?"), not just an icon
- Footer links underlined, not color-only
- Page works without JavaScript (form submits as a standard HTML POST; falls back if JS disabled)

## 9. Form and data

### Two-state form

**State 1 — pre-submit:**
- Single email input
- Single submit button labeled "Where can I go?"
- Standard HTML form, POST to `/api/signup`

**State 2 — post-submit:**
- Replaces the form area
- Cards above keep rotating
- Acknowledgment + 3 optional qualifiers + Share/No-thanks actions
- Qualifier submit POSTs to `/api/qualifiers/<signup_id>`

### Data captured

| Field | Required | Storage |
|---|---|---|
| `email` | yes | `signups.email` |
| `created_at` | auto | `signups.created_at` |
| `ip_hash` | auto (privacy) | `signups.ip_hash` (SHA-256 of IP, for dedup) |
| `referrer` | auto if present | `signups.referrer` |
| `budget_bucket` | no (default: mid) | `qualifiers.budget_bucket` enum: low / mid / stretch |
| `home_airport` | no | `qualifiers.home_airport` (free text in MVP, no validation; normalize server-side on read) |
| `frustration` | no | `qualifiers.frustration` (free text, max 500 chars) |
| `qualifiers_submitted_at` | nullable | `qualifiers.created_at` |

`qualifiers.signup_id` foreign keys to `signups.id`. Qualifier row exists only if the visitor engaged with the post-submit step.

## 10. Implementation architecture (high-level)

The brainstorming spec is intentionally lighter than an implementation plan here. Specifics will be worked out in the next phase (writing-plans).

**Hosting:** Promptiv-main server (already accessible via root SSH).

**Stack:**
- **Frontend:** Static HTML + CSS + minimal vanilla JS + GSAP (CDN initially; self-host before launch). No framework. No build step beyond optional asset minification.
- **Backend:** Small Python Flask app on the same server, behind nginx. Two endpoints: `POST /api/signup`, `POST /api/qualifiers/<signup_id>`.
- **Database:** SQLite, one file at `/var/lib/promptiv/teaser.sqlite`. Schema in section 9.
- **Email:** Resend (Adam already uses Resend; key carried over from the LocalSEO environment or copied into a project-scoped `.env`).
- **Static asset serving:** nginx serves the HTML/CSS/JS directly; Flask handles only the two API endpoints.

**Confirmation email on signup (sent via Resend):**
- Subject: `You're on the list.` (matches the in-page acknowledgment voice)
- Body: 1 short sentence acknowledging the signup, no marketing, no countdown. Exact body deferred to implementation plan.
- From: deferred to implementation plan. Open question (see section 12): reuse `team@mail.distillworks.com` vs set up `team@promptiv.io`.

## 11. Out of scope (defer to implementation plan)

- Specific Flask app file structure
- Exact SQLite schema migrations
- Exact Resend email template HTML
- Privacy policy and Terms of Service page content
- Deploy process (rsync vs git pull vs CI/CD)
- Backup strategy for the SQLite file
- Rate-limiting on the signup endpoint
- Spam filtering on the qualifier textarea
- Analytics (Plausible, GoatCounter, or something else)
- Admin dashboard to view signups
- A/B testing the headline or CTA
- Mobile-specific layout adjustments beyond responsive sides

## 12. Open questions (not blockers, but record them now)

1. **Sender domain for Resend.** Use existing `team@mail.distillworks.com` for the confirmation email, or set up `team@promptiv.io` as a sender? The implementation plan should choose.
2. **GDPR / CAN-SPAM posture.** Self-hosting means owning the unsubscribe + data-deletion flow. The teaser is small enough to defer most of this until product launch, but the privacy policy should at least name a contact email for deletion requests.
3. **What happens after the user clicks "No thanks" on the qualifiers?** Currently the design just dismisses; the email stays in `signups` without any qualifier row. Confirm this is intended.
4. **What if a visitor signs up twice with the same email?** Plan should specify dedup behavior (silently update timestamp, send a different "you're already on the list" email, or error).
5. **Promptiv-main has 347 days of uptime.** Before deploying anything new, recommend a kernel + OS update and a reboot. Coordinate with launch timing.

---

*This spec defines the design only. Implementation plan with full file structure, endpoint behavior, deploy process, and test plan comes next via `superpowers:writing-plans`.*
