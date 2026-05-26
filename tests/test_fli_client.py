"""Tests for the fli wrapper. Uses mock mode — never hits real Google."""
from datetime import date

from server.fli_client import FliClient, FliResult


def test_mock_search_dates_returns_results():
    client = FliClient(mock=True)
    results = client.search_dates(
        origin="BNA",
        destination="CDMX",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 30),
        trip_nights=7,
    )
    assert len(results) >= 1
    assert all(isinstance(r, FliResult) for r in results)
    assert results[0].total_price_usd > 0
    assert results[0].trip_nights == 7
    assert results[0].origin_iata == "BNA"
    assert results[0].dest_iata == "CDMX"


def test_mock_returns_sorted_by_price():
    client = FliClient(mock=True)
    results = client.search_dates(
        origin="JFK", destination="LIS",
        start_date=date(2026, 7, 1), end_date=date(2026, 9, 30),
        trip_nights=10,
    )
    prices = [r.total_price_usd for r in results]
    assert prices == sorted(prices)


def test_mock_can_simulate_empty_response():
    """When origin/dest looks malformed, mock returns empty (mirror real-world behavior)."""
    client = FliClient(mock=True)
    results = client.search_dates(
        origin="XXX", destination="YYY",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 30),
        trip_nights=7,
    )
    assert results == []
