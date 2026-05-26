"""Pure ranking function for /api/go. No DB, no I/O."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Candidate:
    iata: str
    price_usd: int
    vibes: list[str]
    novelty_score: int
    cheapest_date_in_best_months: bool


@dataclass(frozen=True)
class UserQuery:
    origin_iata: str
    budget_usd: int
    trip_nights: int
    vibes: list[str]


@dataclass
class SessionState:
    seen_count: dict[str, int] = field(default_factory=dict)


def score(candidate: Candidate, query: UserQuery, session: SessionState) -> Optional[float]:
    """Return weighted score, or None if filtered out (>15% over budget)."""
    ratio = candidate.price_usd / query.budget_usd

    if 0.70 <= ratio <= 1.00:
        budget_fit = 1.0
    elif 0.50 <= ratio < 0.70:
        budget_fit = 0.6
    elif ratio < 0.50:
        budget_fit = 0.4
    elif 1.00 < ratio <= 1.15:
        budget_fit = 0.5
    else:
        return None

    seen = session.seen_count.get(candidate.iata, 0)
    if seen == 0:
        novelty = 1.0
    elif seen == 1:
        novelty = 0.6
    else:
        novelty = 0.3

    if not query.vibes:
        vibe_match = 1.0
    else:
        overlap = len(set(query.vibes) & set(candidate.vibes))
        vibe_match = min(1.0, 0.5 + (0.15 * overlap))

    seasonality = 1.0 if candidate.cheapest_date_in_best_months else 0.6

    novelty_bonus = 1.0 + (candidate.novelty_score - 3) * 0.05

    return budget_fit * novelty * vibe_match * seasonality * novelty_bonus
