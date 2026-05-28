from scraper.base import parse_price_usd, parse_area_sotka


def test_parse_price_usd_dollar_sign():
    assert parse_price_usd("15 000 $") == 15000.0


def test_parse_price_usd_no_spaces():
    assert parse_price_usd("15000$") == 15000.0


def test_parse_price_usd_kgs():
    result = parse_price_usd("1 305 000 сом", usd_kgs_rate=87.0)
    assert result == round(1305000 / 87.0, 2)


def test_parse_price_usd_returns_none_on_garbage():
    assert parse_price_usd("Цена по договорённости") is None


def test_parse_area_sotka_basic():
    assert parse_area_sotka("8 соток") == 8.0


def test_parse_area_sotka_abbreviation():
    assert parse_area_sotka("8 сот.") == 8.0


def test_parse_area_sotka_ga():
    assert parse_area_sotka("0.08 га") == 8.0


def test_parse_area_sotka_none_on_garbage():
    assert parse_area_sotka("площадь не указана") is None


def test_parse_price_usd_usd_suffix():
    assert parse_price_usd("15000 USD") == 15000.0
