import verify_sdjwt

from ap2_shared.keys import generate_p256_keypair
from ap2_shared.sdjwt import (
    attach_kb,
    build_presentation,
    make_disclosure,
    make_kb_jwt,
    verify,
)

import build_sdjwt


def test_credential_round_trip_reveals_only_subset():
    issuer_priv, issuer_pub = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    assert set(disclosures.keys()) == set(build_sdjwt.SD_CLAIMS)

    pres = build_sdjwt.hold_and_present(
        sdjwt, disclosures,
        reveal=["country", "over_18"],
        holder_priv=holder_priv, holder_kid="alice-1",
        aud="merchant.example", nonce="txn-001", now=1700000000,
    )
    out = verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="merchant.example", expected_nonce="txn-001",
    )
    assert out is not None
    assert out["country"] == "CA"
    assert out["over_18"] is True
    # The unrevealed claims must NOT leak.
    for hidden in ("name", "account_id", "account_tier"):
        assert hidden not in out


def test_lesson_valid_presentation_verifies():
    issuer_priv, issuer_pub = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    pres = build_sdjwt.hold_and_present(
        sdjwt, disclosures,
        reveal=["country", "over_18"],
        holder_priv=holder_priv, holder_kid="alice-1",
        aud="merchant.example", nonce="txn-001", now=1700000000,
    )
    out = verify_sdjwt.verify_presentation(
        pres, issuer_pub, aud="merchant.example", nonce="txn-001"
    )
    assert out is not None and out["country"] == "CA"


def test_lesson_tampered_disclosure_fails():
    issuer_priv, issuer_pub = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    evil, _ = make_disclosure("over_18", False)
    evil_disclosures = dict(disclosures, over_18=evil)
    pres_no_kb = build_presentation(
        sdjwt_token=sdjwt, disclosures=evil_disclosures,
        reveal=["country", "over_18"],
    )
    kb = make_kb_jwt(
        presentation_no_kb=pres_no_kb,
        aud="merchant.example", nonce="txn-001",
        holder_priv=holder_priv, holder_kid="alice-1", now=1700000000,
    )
    pres = attach_kb(pres_no_kb, kb)
    assert verify_sdjwt.verify_presentation(
        pres, issuer_pub, aud="merchant.example", nonce="txn-001"
    ) is None


def test_lesson_wrong_holder_key_on_kb_fails():
    issuer_priv, issuer_pub = generate_p256_keypair()
    _, holder_pub = generate_p256_keypair()
    attacker_priv, _ = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    pres_no_kb = build_presentation(
        sdjwt_token=sdjwt, disclosures=disclosures,
        reveal=["country"],
    )
    kb = make_kb_jwt(
        presentation_no_kb=pres_no_kb,
        aud="merchant.example", nonce="txn-001",
        holder_priv=attacker_priv, holder_kid="attacker", now=1700000000,
    )
    pres = attach_kb(pres_no_kb, kb)
    assert verify_sdjwt.verify_presentation(
        pres, issuer_pub, aud="merchant.example", nonce="txn-001"
    ) is None


def test_lesson_missing_kb_when_aud_required_fails():
    issuer_priv, issuer_pub = generate_p256_keypair()
    _, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    pres = build_presentation(
        sdjwt_token=sdjwt, disclosures=disclosures, reveal=["country"]
    )  # no KB attached
    assert verify_sdjwt.verify_presentation(
        pres, issuer_pub, aud="merchant.example", nonce="txn-001"
    ) is None


def test_sdk_open_payment_mandate_flow_verifies():
    # Renamed from `map_to_sdk` to avoid sys.modules collision with Lesson 02's
    # same-named file (hyphenated lesson dirs can't be Python packages).
    import sdjwt_to_sdk
    payloads = sdjwt_to_sdk.open_payment_mandate_flow()
    # The SDK returns a list of per-token effective payloads for chains.
    assert isinstance(payloads, list) and len(payloads) >= 1
