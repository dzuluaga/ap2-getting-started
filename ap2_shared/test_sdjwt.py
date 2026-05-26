import json

from ap2_shared.jose import b64url_decode, sha256_b64url
from ap2_shared.sdjwt import make_disclosure


def test_make_disclosure_round_trips_and_hashes_the_b64_string():
    disc, h = make_disclosure("country", "CA", salt="AAAAAAAAAAAAAAAAAAAAAA")
    salt, name, value = json.loads(b64url_decode(disc))
    assert salt == "AAAAAAAAAAAAAAAAAAAAAA"
    assert name == "country"
    assert value == "CA"
    # The hash is over the base64url-encoded disclosure bytes — what goes in _sd.
    assert h == sha256_b64url(disc.encode("ascii"))


def test_make_disclosure_generates_unique_salts_when_omitted():
    a, _ = make_disclosure("country", "CA")
    b, _ = make_disclosure("country", "CA")
    assert a != b  # Different salts → different disclosures even for same (name, value).
