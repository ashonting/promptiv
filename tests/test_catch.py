from server.catch import compose


def test_compose_base_only():
    assert compose(base="Tokyo is expensive in cherry blossom season.", route=None) \
        == "Tokyo is expensive in cherry blossom season."


def test_compose_base_plus_route():
    out = compose(
        base="It's a city, not a beach.",
        route="BNA->MEX routes via DFW.",
    )
    assert out == "It's a city, not a beach. BNA->MEX routes via DFW."


def test_compose_route_only():
    assert compose(base=None, route="BNA->NRT is 16h door-to-door.") \
        == "BNA->NRT is 16h door-to-door."


def test_compose_both_null_returns_none():
    assert compose(base=None, route=None) is None


def test_compose_strips_whitespace():
    assert compose(base="  hello  ", route="  world  ") == "hello world"
