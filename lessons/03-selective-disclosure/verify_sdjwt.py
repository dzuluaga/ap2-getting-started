"""Lesson 03 — Verify an SD-JWT presentation, with four failure-mode demos.

A presentation is trustworthy only when *three* checks pass:
1. **Authenticity** — the SD-JWT signature is valid under the issuer's key.
2. **Holder binding** — the KB-JWT is signed by the key in the SD-JWT's
   ``cnf``, and its ``sd_hash`` covers the exact presentation it accompanies
   (swap disclosures → broken).
3. **Selective disclosure integrity** — every presented disclosure hashes to
   a value already in the issuer-signed ``_sd`` array. The holder cannot
   forge new claims or change values.
"""
from __future__ import annotations

from ap2_shared.keys import generate_p256_keypair
from ap2_shared.sdjwt import (
    attach_kb,
    build_presentation,
    make_disclosure,
    make_kb_jwt,
    verify,
)

import build_sdjwt


def verify_presentation(presentation, issuer_pub, *, aud, nonce):
    """Verify a presentation, requiring KB with matching (aud, nonce)."""
    return verify(
        presentation=presentation,
        issuer_pub=issuer_pub,
        expected_aud=aud,
        expected_nonce=nonce,
    )


def main() -> None:
    issuer_priv, issuer_pub = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    aud, nonce = "merchant.example", "txn-001"

    # 1) Valid presentation.
    pres = build_sdjwt.hold_and_present(
        sdjwt, disclosures,
        reveal=["country", "over_18"],
        holder_priv=holder_priv, holder_kid="alice-1",
        aud=aud, nonce=nonce,
    )
    print(
        "Valid presentation verifies:",
        verify_presentation(pres, issuer_pub, aud=aud, nonce=nonce) is not None,
    )

    # 2) Tampered disclosure (swap over_18=True for over_18=False).
    evil, _ = make_disclosure("over_18", False)
    evil_disclosures = dict(disclosures, over_18=evil)
    evil_pres_no_kb = build_presentation(
        sdjwt_token=sdjwt, disclosures=evil_disclosures,
        reveal=["country", "over_18"],
    )
    evil_kb = make_kb_jwt(
        presentation_no_kb=evil_pres_no_kb, aud=aud, nonce=nonce,
        holder_priv=holder_priv, holder_kid="alice-1",
    )
    print(
        "Tampered disclosure verifies:",
        verify_presentation(attach_kb(evil_pres_no_kb, evil_kb),
                            issuer_pub, aud=aud, nonce=nonce),
        "(expected None)",
    )

    # 3) Wrong holder key on KB (attacker key, not the cnf key).
    attacker_priv, _ = generate_p256_keypair()
    bad_pres_no_kb = build_presentation(
        sdjwt_token=sdjwt, disclosures=disclosures, reveal=["country"]
    )
    bad_kb = make_kb_jwt(
        presentation_no_kb=bad_pres_no_kb, aud=aud, nonce=nonce,
        holder_priv=attacker_priv, holder_kid="attacker",
    )
    print(
        "Wrong-key KB verifies:",
        verify_presentation(attach_kb(bad_pres_no_kb, bad_kb),
                            issuer_pub, aud=aud, nonce=nonce),
        "(expected None)",
    )

    # 4) Missing KB when aud/nonce are required.
    no_kb = build_presentation(
        sdjwt_token=sdjwt, disclosures=disclosures, reveal=["country"]
    )
    print(
        "Missing KB verifies:",
        verify_presentation(no_kb, issuer_pub, aud=aud, nonce=nonce),
        "(expected None)",
    )


if __name__ == "__main__":
    main()
