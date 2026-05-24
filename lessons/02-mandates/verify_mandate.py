"""Lesson 02 — Verify a Checkout Mandate.

Two independent checks make the mandate trustworthy:
1. The merchant's signature over the JWT is valid (authenticity).
2. The `cart_hash` claim still matches the cart contents (integrity) — so a
   tampered cart is detected even though the signature itself is intact.
"""
from __future__ import annotations

from ap2_shared.jose import canonical_json, sha256_b64url, verify_jwt
from ap2_shared.keys import generate_p256_keypair

import build_mandate


def verify_checkout_mandate(checkout_mandate: dict, merchant_public_key) -> bool:
    payload = verify_jwt(
        checkout_mandate["merchant_authorization"], merchant_public_key
    )
    if payload is None:
        return False
    recomputed = sha256_b64url(canonical_json(checkout_mandate["contents"]))
    return payload.get("cart_hash") == recomputed


def main() -> None:
    priv, pub = generate_p256_keypair()
    cart = build_mandate.build_cart_contents(
        cart_id="cart_123",
        merchant_name="Cat Store",
        item_label="Catnip Deluxe",
        amount=49.99,
        currency="USD",
        payment_request_id="pr_123",
        cart_expiry="2099-01-01T00:00:00Z",
    )
    mandate = build_mandate.build_checkout_mandate(cart, priv, "m-1")
    print("Valid mandate verifies:", verify_checkout_mandate(mandate, pub))

    mandate["contents"]["payment_request"]["details"]["total"]["amount"][
        "value"
    ] = 0.01
    print(
        "Tampered mandate verifies:",
        verify_checkout_mandate(mandate, pub),
        "(expected False)",
    )


if __name__ == "__main__":
    main()
