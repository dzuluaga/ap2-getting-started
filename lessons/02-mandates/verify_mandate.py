"""Lesson 02 — Verify the mandates.

A Checkout Mandate is trustworthy when two independent checks pass:
1. The merchant's signature over the JWT is valid (authenticity).
2. The `cart_hash` claim still matches the cart contents (integrity) — so a
   tampered cart is detected even though the signature itself is intact.

A Payment Mandate adds a third idea — binding. It is trustworthy when:
1. The user's signature over the JWT is valid (authenticity).
2. The payment-contents hash still matches (integrity).
3. It carries the hash of *this* Checkout Mandate's signed JWT, so the payment
   is bound to the exact checkout it authorizes — not some other cart.
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


def verify_payment_mandate(
    payment_mandate: dict, user_public_key, checkout_mandate: dict
) -> bool:
    """Verify the user's signature, the payment-contents hash, and the binding
    to a specific Checkout Mandate (all three must hold)."""
    payload = verify_jwt(
        payment_mandate["user_authorization"], user_public_key
    )
    if payload is None:
        return False  # authenticity
    transaction_data = payload.get("transaction_data", [])
    payment_hash = sha256_b64url(
        canonical_json(payment_mandate["payment_mandate_contents"])
    )
    checkout_hash = sha256_b64url(
        checkout_mandate["merchant_authorization"].encode("ascii")
    )
    # integrity (payment contents) AND binding (to this checkout)
    return payment_hash in transaction_data and checkout_hash in transaction_data


def main() -> None:
    merchant_priv, merchant_pub = generate_p256_keypair()
    user_priv, user_pub = generate_p256_keypair()
    cart = build_mandate.build_cart_contents(
        cart_id="cart_123",
        merchant_name="Cat Store",
        item_label="Catnip Deluxe",
        amount=49.99,
        currency="USD",
        payment_request_id="pr_123",
        cart_expiry="2099-01-01T00:00:00Z",
    )
    checkout = build_mandate.build_checkout_mandate(cart, merchant_priv, "m-1")
    print(
        "Valid checkout mandate verifies:",
        verify_checkout_mandate(checkout, merchant_pub),
    )

    # Authenticity: a checkout signed by the wrong key fails verification.
    attacker_priv, _ = generate_p256_keypair()
    forged = build_mandate.build_checkout_mandate(cart, attacker_priv, "attacker")
    print(
        "Forged-signer checkout verifies:",
        verify_checkout_mandate(forged, merchant_pub),
        "(expected False)",
    )

    # Payment Mandate: valid when checked against the checkout it binds to...
    payment = build_mandate.build_payment_mandate(checkout, user_priv, "u-1")
    print(
        "Valid payment mandate verifies:",
        verify_payment_mandate(payment, user_pub, checkout),
    )

    # ...but fails against a different checkout (binding is broken).
    other_checkout = build_mandate.build_checkout_mandate(cart, merchant_priv, "m-1")
    print(
        "Payment vs wrong checkout verifies:",
        verify_payment_mandate(payment, user_pub, other_checkout),
        "(expected False)",
    )

    # Integrity: tampering with the cart after signing fails verification.
    checkout["contents"]["payment_request"]["details"]["total"]["amount"][
        "value"
    ] = 0.01
    print(
        "Tampered checkout verifies:",
        verify_checkout_mandate(checkout, merchant_pub),
        "(expected False)",
    )


if __name__ == "__main__":
    main()
