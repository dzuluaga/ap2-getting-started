"""Lesson 03 — Issue an SD-JWT credential and present it selectively.

The story: "Bank of Examples" issues Alice a credential with five claims, all
selectively disclosable. Alice (the holder) presents to a merchant revealing
only `country` and `over_18`, with a KB-JWT binding the presentation to the
merchant for this specific transaction.

SD-JWT vocab to keep in your head while reading:
- Disclosure: `base64url(json([salt, name, value]))`. The holder may show it.
- `_sd`: array of disclosure hashes inside the issuer-signed SD-JWT — locks
  which claims exist (even when their values are not yet revealed).
- `cnf`: confirmation key — the holder's public JWK, carried in the SD-JWT.
- KB-JWT: signed by the holder for a given `(aud, nonce, sd_hash)`.
"""
from __future__ import annotations

from ap2_shared.keys import generate_p256_keypair
from ap2_shared.sdjwt import (
    attach_kb,
    build_presentation,
    make_kb_jwt,
    make_sdjwt,
)


SD_CLAIMS = ["name", "country", "account_id", "over_18", "account_tier"]


def issue_credential(issuer_priv, issuer_kid, holder_pub):
    """Bank of Examples issues Alice's credential."""
    payload = {
        "iss": "Bank of Examples",
        "sub": "user_alice",
        "name": "Alice Example",
        "country": "CA",
        "account_id": "AE-9001",
        "over_18": True,
        "account_tier": "gold",
    }
    return make_sdjwt(
        payload=payload,
        sd_claims=SD_CLAIMS,
        issuer_priv=issuer_priv,
        issuer_kid=issuer_kid,
        holder_pub=holder_pub,
    )


def hold_and_present(
    sdjwt_token,
    disclosures,
    *,
    reveal,
    holder_priv,
    holder_kid,
    aud,
    nonce,
    now=None,
):
    """Holder picks which claims to reveal + signs a KB binding the
    presentation to (aud, nonce)."""
    presentation_no_kb = build_presentation(
        sdjwt_token=sdjwt_token,
        disclosures=disclosures,
        reveal=reveal,
    )
    kb = make_kb_jwt(
        presentation_no_kb=presentation_no_kb,
        aud=aud,
        nonce=nonce,
        holder_priv=holder_priv,
        holder_kid=holder_kid,
        now=now,
    )
    return attach_kb(presentation_no_kb, kb)


def main() -> None:
    issuer_priv, _ = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = issue_credential(issuer_priv, "bank-1", holder_pub)
    print("SD-JWT issued by 'Bank of Examples'.")
    print("Selectively-disclosable claims:", list(disclosures.keys()))

    pres = hold_and_present(
        sdjwt, disclosures,
        reveal=["country", "over_18"],
        holder_priv=holder_priv,
        holder_kid="alice-1",
        aud="merchant.example",
        nonce="txn-001",
    )
    print("\nHolder presents to merchant (revealing country, over_18 only):")
    print(pres)


if __name__ == "__main__":
    main()
