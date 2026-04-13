"""schemas_admin parsing."""

import pytest

from backend_api.schemas import ModelMetadata
from backend_api.schemas_admin import parse_driver_config_form, parse_metadata_form


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


def test_parse_metadata_none():
    assert parse_metadata_form(None) is None
    assert parse_metadata_form("") is None
    assert parse_metadata_form("   ") is None


def test_parse_metadata_round_trip():
    raw = '{"card":{"title":"T","summary":"S"},"analysis":{"feature_band_names":["a","b"]}}'
    m = parse_metadata_form(raw)
    assert isinstance(m, ModelMetadata)
    assert m.card is not None and m.card.title == "T"
    assert m.analysis is not None and m.analysis.feature_band_names == ["a", "b"]


def test_parse_metadata_not_object():
    with pytest.raises(ValueError, match="JSON object"):
        parse_metadata_form("[1,2]")


def test_parse_metadata_invalid_json():
    with pytest.raises(ValueError, match="valid JSON"):
        parse_metadata_form("not json")


def test_parse_metadata_validation_error():
    with pytest.raises(ValueError):
        parse_metadata_form('{"card":"not-an-object"}')
