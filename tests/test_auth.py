from datetime import datetime, timedelta, timezone

from app.auth import authenticate, hash_password, session_is_valid, verify_password


def test_password_hash_round_trip():
    encoded = hash_password("secret")
    assert verify_password("secret", encoded)
    assert not verify_password("wrong", encoded)


def test_authentication_is_read_only_role():
    user = authenticate("demo", "pass", "demo", "pass")
    assert user is not None
    assert user.role == "read_only_service"


def test_session_ttl():
    assert session_is_valid(datetime.now(timezone.utc), 60)
    assert not session_is_valid(datetime.now(timezone.utc) - timedelta(minutes=61), 60)
