"""schemas_admin parsing."""

import pytest

from backend_api.schemas_admin import parse_driver_config_form


def test_parse_driver_config_none():
    assert parse_driver_config_form(None) is None
    assert parse_driver_config_form("") is None
    assert parse_driver_config_form("   ") is None


def test_parse_driver_config_object():
    assert parse_driver_config_form('{"a": 1}') == {"a": 1}


def test_parse_driver_config_not_object():
    with pytest.raises(ValueError, match="JSON object"):
        parse_driver_config_form("[1,2]")


def test_parse_driver_config_invalid_json():
    with pytest.raises(ValueError, match="valid JSON"):
        parse_driver_config_form("not json")
