import json

from ap2_shared.jose import (
    b64url_decode,
    decode_jwt_unverified,
    sha256_b64url,
    verify_jwt,
)
from ap2_shared.keys import generate_p256_keypair
from ap2_shared.sdjwt import (
    attach_kb,
    build_presentation,
    make_disclosure,
    make_kb_jwt,
    make_sdjwt,
    verify,
)


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


def _payload():
    return {"iss": "Bank", "sub": "alice", "country": "CA", "over_18": True}


def test_make_sdjwt_moves_sd_claims_to_disclosures_and_adds_sd_array():
    issuer_priv, issuer_pub = generate_p256_keypair()
    token, disclosures = make_sdjwt(
        payload=_payload(),
        sd_claims=["country", "over_18"],
        issuer_priv=issuer_priv,
        issuer_kid="bank-1",
    )
    # Signature is valid under the issuer's key.
    clear = verify_jwt(token, issuer_pub)
    assert clear is not None
    # The selectively-disclosed fields are gone from the clear payload.
    assert "country" not in clear and "over_18" not in clear
    # Their hashes ARE in _sd (one per sd_claim).
    assert isinstance(clear["_sd"], list) and len(clear["_sd"]) == 2
    # Disclosures dict returns one entry per sd_claim, keyed by name.
    assert set(disclosures.keys()) == {"country", "over_18"}


def test_make_sdjwt_includes_cnf_when_holder_pub_provided():
    issuer_priv, _ = generate_p256_keypair()
    _, holder_pub = generate_p256_keypair()
    token, _ = make_sdjwt(
        payload=_payload(),
        sd_claims=["country"],
        issuer_priv=issuer_priv,
        issuer_kid="bank-1",
        holder_pub=holder_pub,
    )
    clear = decode_jwt_unverified(token)
    assert clear["cnf"]["jwk"]["kty"] == "EC"
    assert clear["cnf"]["jwk"]["crv"] == "P-256"


def test_make_sdjwt_raises_when_sd_claim_missing():
    import pytest
    issuer_priv, _ = generate_p256_keypair()
    with pytest.raises(KeyError):
        make_sdjwt(
            payload={"iss": "Bank"},
            sd_claims=["country"],
            issuer_priv=issuer_priv,
            issuer_kid="bank-1",
        )


def test_build_presentation_includes_only_revealed_disclosures():
    issuer_priv, _ = generate_p256_keypair()
    token, disclosures = make_sdjwt(
        payload=_payload(),
        sd_claims=["country", "over_18"],
        issuer_priv=issuer_priv,
        issuer_kid="bank-1",
    )
    pres = build_presentation(
        sdjwt_token=token, disclosures=disclosures, reveal=["country"]
    )
    # Wire format: <sdjwt>~<disclosure>~  (always ends with ~)
    assert pres.endswith("~")
    parts = pres.rstrip("~").split("~")
    assert parts[0] == token
    assert parts[1] == disclosures["country"]
    assert disclosures["over_18"] not in pres


def test_make_kb_jwt_signs_with_typ_kb_jwt_and_correct_sd_hash():
    holder_priv, holder_pub = generate_p256_keypair()
    presentation_no_kb = "ey....jwt~ZGlzYzE~"  # arbitrary; we hash whatever we pass
    kb = make_kb_jwt(
        presentation_no_kb=presentation_no_kb,
        aud="merchant.example",
        nonce="txn-001",
        holder_priv=holder_priv,
        holder_kid="alice-1",
        now=1700000000,
    )
    head = json.loads(b64url_decode(kb.split(".")[0]))
    payload = decode_jwt_unverified(kb)
    assert head["typ"] == "kb+jwt"
    assert head["alg"] == "ES256"
    assert payload["aud"] == "merchant.example"
    assert payload["nonce"] == "txn-001"
    assert payload["iat"] == 1700000000
    assert payload["sd_hash"] == sha256_b64url(presentation_no_kb.encode("ascii"))
    # And the signature verifies under the holder's public key.
    assert verify_jwt(kb, holder_pub) is not None


def test_attach_kb_concatenates_and_keeps_trailing_tilde():
    out = attach_kb("ey....jwt~ZGlzYzE~", "ey....kb")
    assert out == "ey....jwt~ZGlzYzE~ey....kb~"


def _issue_and_present(reveal, *, aud="merchant.example", nonce="txn-001",
                      attacker_kb=False, tamper_country=False):
    """Test helper: issue a credential, present with KB, optionally tamper."""
    issuer_priv, issuer_pub = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    token, disclosures = make_sdjwt(
        payload={"iss": "Bank", "sub": "alice", "country": "CA", "over_18": True},
        sd_claims=["country", "over_18"],
        issuer_priv=issuer_priv, issuer_kid="bank-1",
        holder_pub=holder_pub,
    )
    if tamper_country:
        # Swap country disclosure for one with a different value.
        evil, _ = make_disclosure("country", "ZZ")
        disclosures = dict(disclosures, country=evil)
    pres_no_kb = build_presentation(
        sdjwt_token=token, disclosures=disclosures, reveal=reveal
    )
    if attacker_kb:
        bad_priv, _ = generate_p256_keypair()
        kb = make_kb_jwt(
            presentation_no_kb=pres_no_kb, aud=aud, nonce=nonce,
            holder_priv=bad_priv, holder_kid="bad-1", now=1700000000,
        )
    else:
        kb = make_kb_jwt(
            presentation_no_kb=pres_no_kb, aud=aud, nonce=nonce,
            holder_priv=holder_priv, holder_kid="alice-1", now=1700000000,
        )
    return attach_kb(pres_no_kb, kb), issuer_pub, pres_no_kb


def test_verify_returns_only_revealed_claims():
    pres, issuer_pub, _ = _issue_and_present(reveal=["country", "over_18"])
    out = verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="merchant.example", expected_nonce="txn-001",
    )
    assert out is not None
    assert out["country"] == "CA"
    assert out["over_18"] is True
    assert out["iss"] == "Bank" and out["sub"] == "alice"
    assert "_sd" not in out and "cnf" not in out


def test_verify_rejects_tampered_disclosure():
    pres, issuer_pub, _ = _issue_and_present(reveal=["country"], tamper_country=True)
    assert verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="merchant.example", expected_nonce="txn-001",
    ) is None


def test_verify_rejects_wrong_holder_key_on_kb():
    pres, issuer_pub, _ = _issue_and_present(reveal=["country"], attacker_kb=True)
    assert verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="merchant.example", expected_nonce="txn-001",
    ) is None


def test_verify_rejects_missing_kb_when_aud_required():
    # Build a presentation with no KB.
    issuer_priv, issuer_pub = generate_p256_keypair()
    _, holder_pub = generate_p256_keypair()
    token, disclosures = make_sdjwt(
        payload={"iss": "Bank", "sub": "alice", "country": "CA"},
        sd_claims=["country"],
        issuer_priv=issuer_priv, issuer_kid="bank-1",
        holder_pub=holder_pub,
    )
    pres = build_presentation(
        sdjwt_token=token, disclosures=disclosures, reveal=["country"]
    )
    assert verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="merchant.example",
    ) is None


def test_verify_rejects_mismatched_aud():
    pres, issuer_pub, _ = _issue_and_present(reveal=["country"])
    assert verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="wrong.example", expected_nonce="txn-001",
    ) is None
