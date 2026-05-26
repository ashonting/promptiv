"""Tests for the ranking function. Pure function, easy to test exhaustively."""
from server.ranking import Candidate, UserQuery, SessionState, score


def make_candidate(**overrides):
    base = {
        "iata": "MEX",
        "price_usd": 400,
        "vibes": ["city", "food", "history"],
        "novelty_score": 3,
        "cheapest_date_in_best_months": True,
    }
    base.update(overrides)
    return Candidate(**base)


def make_query(**overrides):
    base = {
        "origin_iata": "BNA",
        "budget_usd": 500,
        "trip_nights": 7,
        "vibes": [],
    }
    base.update(overrides)
    return UserQuery(**base)


def empty_session():
    return SessionState(seen_count={})


def test_score_in_budget_sweet_spot_is_max():
    s = score(make_candidate(price_usd=400), make_query(budget_usd=500), empty_session())
    assert s is not None
    assert 0.95 <= s <= 1.05


def test_score_over_budget_15_percent_returns_none():
    s = score(make_candidate(price_usd=580), make_query(budget_usd=500), empty_session())
    assert s is None


def test_score_too_cheap_is_suspicious():
    s = score(make_candidate(price_usd=200), make_query(budget_usd=500), empty_session())
    assert s is not None
    assert s < 0.5


def test_score_repeat_in_session_drops_novelty():
    candidate = make_candidate(price_usd=400)
    fresh = score(candidate, make_query(budget_usd=500), empty_session())
    seen = score(candidate, make_query(budget_usd=500), SessionState(seen_count={"MEX": 1}))
    assert seen is not None and fresh is not None
    assert seen < fresh


def test_score_vibe_match_increases_score():
    q = make_query(vibes=["city"])
    matching = score(make_candidate(price_usd=400, vibes=["city", "food"]), q, empty_session())
    nonmatching = score(make_candidate(price_usd=400, vibes=["beach"]), q, empty_session())
    assert matching is not None and nonmatching is not None
    assert matching > nonmatching


def test_score_off_season_reduced():
    in_season = score(make_candidate(cheapest_date_in_best_months=True), make_query(), empty_session())
    off = score(make_candidate(cheapest_date_in_best_months=False), make_query(), empty_session())
    assert off is not None and in_season is not None
    assert off < in_season


def test_score_novelty_bonus_rewards_unknown():
    cliche = score(make_candidate(novelty_score=1), make_query(), empty_session())
    novel = score(make_candidate(novelty_score=5), make_query(), empty_session())
    assert cliche is not None and novel is not None
    assert novel > cliche
