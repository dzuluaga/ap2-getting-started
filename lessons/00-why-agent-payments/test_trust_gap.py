from ap2_shared.jose import verify_jwt
from ap2_shared.keys import generate_p256_keypair

import trust_gap


def test_unverifiable_claim_has_no_proof():
    claim = trust_gap.unverifiable_claim()
    assert claim["proof"] is None


def test_verifiable_claim_is_signed_and_checks_out():
    priv, pub = generate_p256_keypair()
    claim = trust_gap.verifiable_claim(priv, "u-1")
    assert verify_jwt(claim["proof"], pub) is not None
