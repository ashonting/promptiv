"""Thin wrapper around the fli Python package (PyPI name: 'flights').

Real mode talks to Google via reverse-engineered API. Mock mode returns
synthetic data for tests. If fli's API changes, _real_search is the only
place to update. See scripts/spike_fli.py for the discovered API shape.
"""
import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass(frozen=True)
class FliResult:
    origin_iata: str
    dest_iata: str
    departure_date: str           # ISO YYYY-MM-DD
    return_date: str              # ISO YYYY-MM-DD
    trip_nights: int
    total_price_usd: int
    stops: Optional[int] = None   # SearchDates does not return this; populated in v1.1
    carrier_codes: Optional[list[str]] = None  # same as stops


class FliError(Exception):
    """Wrapper for fli errors that we treat as recoverable in the cron."""


class FliClient:
    def __init__(self, mock: bool = False):
        self.mock = mock

    def search_dates(
        self,
        origin: str,
        destination: str,
        start_date: date,
        end_date: date,
        trip_nights: int,
    ) -> list[FliResult]:
        if self.mock:
            return self._mock_search(origin, destination, start_date, end_date, trip_nights)
        return self._real_search(origin, destination, start_date, end_date, trip_nights)

    def _mock_search(self, origin, destination, start_date, end_date, trip_nights):
        if any(c in ("XXX", "YYY") or not c.isalpha()
               for c in (origin, destination)):
            return []
        rng = random.Random(f"{origin}-{destination}-{trip_nights}")
        base_price = 200 + rng.randint(0, 1200)
        results = []
        cursor = start_date
        while cursor + timedelta(days=trip_nights) <= end_date:
            jitter = rng.randint(-80, 200)
            price = max(120, base_price + jitter)
            results.append(FliResult(
                origin_iata=origin,
                dest_iata=destination,
                departure_date=cursor.isoformat(),
                return_date=(cursor + timedelta(days=trip_nights)).isoformat(),
                trip_nights=trip_nights,
                total_price_usd=price,
            ))
            cursor += timedelta(days=7)
        results.sort(key=lambda r: r.total_price_usd)
        return results

    def _real_search(self, origin, destination, start_date, end_date, trip_nights):
        # Implementation mirrors scripts/spike_fli.py exactly.
        try:
            from fli.models import DateSearchFilters, PassengerInfo
            from fli.models.airport import Airport
            from fli.core.builders import build_date_search_segments
            from fli.search import SearchDates
        except ImportError as e:
            raise FliError(f"fli package not installed: {e}") from e

        try:
            origin_airport = getattr(Airport, origin)
            dest_airport = getattr(Airport, destination)
        except AttributeError as e:
            raise FliError(f"unknown IATA in fli.Airport: {e}") from e

        try:
            segments, trip_type = build_date_search_segments(
                origin=origin_airport,
                destination=dest_airport,
                start_date=start_date.isoformat(),
                trip_duration=trip_nights,
                is_round_trip=True,
            )
            filters = DateSearchFilters(
                trip_type=trip_type,
                passenger_info=PassengerInfo(adults=1),
                flight_segments=segments,
                from_date=start_date.isoformat(),
                to_date=end_date.isoformat(),
                duration=trip_nights,
            )
            raw = SearchDates().search(filters, currency="USD")
        except Exception as e:
            raise FliError(f"fli call failed for {origin}->{destination}: {e}") from e

        if raw is None:
            return []

        out: list[FliResult] = []
        for dp in raw:
            # DatePrice: date is tuple(datetime, datetime) for round-trip; price is float
            try:
                dep_dt, ret_dt = dp.date
            except (TypeError, ValueError):
                continue  # unexpected single-element tuple, skip
            out.append(FliResult(
                origin_iata=origin,
                dest_iata=destination,
                departure_date=dep_dt.date().isoformat(),
                return_date=ret_dt.date().isoformat(),
                trip_nights=trip_nights,
                total_price_usd=int(round(dp.price)),
            ))
        out.sort(key=lambda r: r.total_price_usd)
        return out
