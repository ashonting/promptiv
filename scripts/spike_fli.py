"""One-shot check: does the `fli` package still talk to Google Flights?

This is Task 1 of the Promptiv v1 plan. The whole product depends on `fli`
(the unofficial reverse-engineered Google Flights client, PyPI package name
`flights`, top-level Python module `fli`). If Google has broken the
reverse-engineering, we need to know before investing 3 weeks of work.

The plan's example used `from flights import SearchDates` with kwargs. The
actual API is different: the PyPI package `flights==0.9.0` installs as the
top-level module `fli`, and `SearchDates.search()` takes a single
`DateSearchFilters` pydantic model rather than kwargs. The MCP server in
`fli.mcp.server` is the reference for how to build the filter; we follow
that pattern here.
"""

from datetime import date, timedelta

from fli.models import (
    DateSearchFilters,
    PassengerInfo,
)
from fli.models.airport import Airport
from fli.core.builders import build_date_search_segments
from fli.search import SearchDates

ORIGIN = Airport.BNA  # Nashville
DESTINATION = Airport.MEX  # Mexico City (CDMX)
TRIP_DURATION = 7

today = date.today()
window_start = today + timedelta(days=14)  # at least a couple weeks out
window_end = window_start + timedelta(days=45)  # stay under MAX_DAYS_PER_SEARCH=61

segments, trip_type = build_date_search_segments(
    origin=ORIGIN,
    destination=DESTINATION,
    start_date=window_start.isoformat(),
    trip_duration=TRIP_DURATION,
    is_round_trip=True,
)

filters = DateSearchFilters(
    trip_type=trip_type,
    passenger_info=PassengerInfo(adults=1),
    flight_segments=segments,
    from_date=window_start.isoformat(),
    to_date=window_end.isoformat(),
    duration=TRIP_DURATION,
)

client = SearchDates()
results = client.search(filters, currency="USD")

if results is None:
    print("BLOCKED: fli returned None — either Google changed the wire format "
          "or the request was rejected. Inspect raw response in fli.search.dates.")
    raise SystemExit(2)

print(f"Got {len(results)} results")
results_sorted = sorted(results, key=lambda r: r.price)
for r in results_sorted[:5]:
    print(r)


# ---------------------------------------------------------------------------
# Actual return shape (captured 2026-05-26 from a successful run against
# Google Flights, BNA <-> MEX, 7-day round-trip, departure window
# 2026-06-09 .. 2026-07-24):
#
# Each result is a `fli.search.dates.DatePrice` pydantic model:
#
#   DatePrice(
#       date=(datetime(2026, 7, 13, 0, 0), datetime(2026, 7, 20, 0, 0)),
#       price=438.0,
#       currency='USD',
#   )
#
# Field summary for Task 6 (`fli_client.py`):
#   - `date` is a tuple. ONE_WAY -> 1-tuple of datetime (departure date).
#     ROUND_TRIP -> 2-tuple (departure_date, return_date).
#   - `price` is a float in the requested currency.
#   - `currency` is an ISO 4217 code string (or None if the API omits it).
#   - `SearchDates.search()` returns `list[DatePrice] | None`. None means
#     the request returned an unexpected payload shape (treat as failure).
#
# Sample output from the run that produced this comment:
#   Got 46 results
#   date=(datetime.datetime(2026, 7, 13, 0, 0), datetime.datetime(2026, 7, 20, 0, 0)) price=438.0 currency='USD'
#   date=(datetime.datetime(2026, 7, 10, 0, 0), datetime.datetime(2026, 7, 17, 0, 0)) price=467.0 currency='USD'
#   date=(datetime.datetime(2026, 7, 20, 0, 0), datetime.datetime(2026, 7, 27, 0, 0)) price=467.0 currency='USD'
#   date=(datetime.datetime(2026, 7, 17, 0, 0), datetime.datetime(2026, 7, 24, 0, 0)) price=486.0 currency='USD'
#   date=(datetime.datetime(2026, 7,  3, 0, 0), datetime.datetime(2026, 7, 10, 0, 0)) price=533.0 currency='USD'
# ---------------------------------------------------------------------------
