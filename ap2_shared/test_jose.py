from ap2_shared.jose import (
    b64url_encode, b64url_decode, canonical_json, sha256_b64url,
    make_jwt, verify_jwt, decode_jwt_unverified,
)
from ap2_shared.keys import generate_p256_keypair


def test_b64url_roundtrip_no_padding():
    s = b64url_encode(b"hello?>")
    assert "=" not in s
    assert b64url_decode(s) == b"hello?>"


def test_canonical_json_is_sorted_and_compact():
    assert canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def test_sha256_b64url_is_stable():
    assert sha256_b64url(b"abc") == sha256_b64url(b"abc")
    assert sha256_b64url(b"abc") != sha256_b64url(b"abd")


def test_sha256_b64url_known_value():
    # SHA-256("abc") is a well-known test vector.
    assert sha256_b64url(b"abc") == "ungWv48Bz-pBQUDeXa4iI7ADYaOWF3qctBD_YfIAFa0"


def test_jwt_sign_and_verify_roundtrip():
    priv, pub = generate_p256_keypair()
    token = make_jwt({"iss": "merchant", "amount": 4999}, priv, kid="m-1")
    payload = verify_jwt(token, pub)
    assert payload is not None
    assert payload["iss"] == "merchant"
    assert decode_jwt_unverified(token)["amount"] == 4999


def test_verify_fails_on_tampered_signature():
    priv, pub = generate_p256_keypair()
    token = make_jwt({"iss": "merchant"}, priv, kid="m-1")
    head, body, sig = token.split(".")
    flipped = sig[:-2] + ("AA" if sig[-2:] != "AA" else "BB")
    assert verify_jwt(f"{head}.{body}.{flipped}", pub) is None


def test_verify_fails_with_wrong_key():
    priv, _ = generate_p256_keypair()
    _, other_pub = generate_p256_keypair()
    token = make_jwt({"iss": "merchant"}, priv, kid="m-1")
    assert verify_jwt(token, other_pub) is None


def test_verify_fails_on_tampered_payload():
    # Swapping the payload body invalidates the signature: the signature
    # covers header.payload, not just the signature segment.
    priv, pub = generate_p256_keypair()
    token = make_jwt({"iss": "merchant", "amount": 100}, priv, kid="m-1")
    head, _, sig = token.split(".")
    evil = b64url_encode(canonical_json({"iss": "merchant", "amount": 9999}))
    assert verify_jwt(f"{head}.{evil}.{sig}", pub) is None
