from ap2_shared.keys import generate_p256_keypair
from ap2_shared.sdjwt import verify

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
