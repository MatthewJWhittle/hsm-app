"""Firebase claim normalization."""

from backend_api.auth_claims import subject_uid_from_claims


def test_subject_uid_prefers_uid_then_sub_then_user_id():
    assert subject_uid_from_claims({"uid": "a", "sub": "b"}) == "a"
    assert subject_uid_from_claims({"sub": "b", "user_id": "c"}) == "b"
    assert subject_uid_from_claims({"user_id": "c"}) == "c"


def test_subject_uid_ignores_empty_strings():
    assert subject_uid_from_claims({"uid": "", "sub": "x"}) == "x"
    assert subject_uid_from_claims({}) is None
    assert subject_uid_from_claims(None) is None
