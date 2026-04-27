from datetime import date, datetime

from opentodo.constants import DEFAULT_PROJECT_ICON
from opentodo.parsing import (
    format_iso_datetime,
    parse_csv_bool,
    parse_due_at,
    parse_due_date,
    parse_iso_datetime,
    parse_project_icon,
    parse_tag_color,
)


def test_parse_due_date_accepts_iso_date():
    assert parse_due_date("2026-04-27") == date(2026, 4, 27)


def test_parse_due_date_returns_none_for_empty_or_invalid_value():
    assert parse_due_date("") is None
    assert parse_due_date("not-a-date") is None


def test_parse_due_at_accepts_iso_datetime():
    assert parse_due_at("2026-04-27T17:30:00") == datetime(2026, 4, 27, 17, 30)


def test_parse_due_at_returns_none_for_empty_or_invalid_value():
    assert parse_due_at(" ") is None
    assert parse_due_at("tomorrow") is None


def test_parse_project_icon_accepts_known_icon_key():
    assert parse_project_icon("work") == "work"


def test_parse_project_icon_falls_back_to_default_icon():
    assert parse_project_icon("unknown") == DEFAULT_PROJECT_ICON


def test_parse_tag_color_normalizes_hex_colors():
    assert parse_tag_color("#ABCDEF") == "#abcdef"
    assert parse_tag_color("#abc") == "#aabbcc"


def test_parse_tag_color_falls_back_for_invalid_colors():
    assert parse_tag_color("red") == "#5b7cfa"
    assert parse_tag_color("#12") == "#5b7cfa"


def test_format_iso_datetime_returns_empty_string_for_none():
    assert format_iso_datetime(None) == ""


def test_parse_iso_datetime_accepts_valid_value():
    assert parse_iso_datetime("2026-04-27T17:30:00") == datetime(2026, 4, 27, 17, 30)


def test_parse_csv_bool_accepts_common_true_values():
    assert parse_csv_bool("1") is True
    assert parse_csv_bool("TRUE") is True
    assert parse_csv_bool("yes") is True
    assert parse_csv_bool("y") is True
    assert parse_csv_bool("0") is False
