"""Lesson 02 — Build a Checkout Mandate and a Payment Mandate by hand.

A *mandate* is signed, hash-bound intent. Here we build two:

* Checkout Mandate — the merchant signs (as a plain JWT) a hash of the cart
  contents, guaranteeing the items and price. The SDK calls the data model
  `CartMandate`; the spec/docs now say "Checkout Mandate" (terminology
  evolved). The signed JWT is the `merchant_authorization` field.
* Payment Mandate — authorizes payment for that checkout, binding to the
  checkout via the hash of the merchant's signed JWT.

We sign with a *plain* ES256 JWT. In real AP2 the user's authorization is an
SD-JWT verifiable presentation (selective disclosure) — that is Lesson 03.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from ap2_shared.jose import canonical_json, make_jwt, sha256_b64url
from ap2_shared.keys import generate_p256_keypair


def build_cart_contents(
    *,
    cart_id: str,
    merchant_name: str,
    item_label: str,
    amount: float,
    currency: str,
    payment_request_id: str,
    cart_expiry: str,
) -> dict:
    """A dict mirroring the SDK's CartContents (with a W3C PaymentRequest)."""
    total = {"label": "Total", "amount": {"currency": currency, "value": amount}}
    return {
        "id": cart_id,
        "user_cart_confirmation_required": True,
        "payment_request": {
            "method_data": [{"supported_methods": "card", "data": {}}],
            "details": {
                "id": payment_request_id,
                "display_items": [
                    {
                        "label": item_label,
                        "amount": {"currency": currency, "value": amount},
                    }
                ],
                "total": total,
            },
        },
        "cart_expiry": cart_expiry,
        "merchant_name": merchant_name,
    }


def build_checkout_mandate(
    cart_contents: dict, merchant_private_key, merchant_kid: str
) -> dict:
    """Sign a hash of the cart as the merchant's authorization JWT."""
    now = int(datetime.now(UTC).timestamp())
    cart_hash = sha256_b64url(canonical_json(cart_contents))
    authorization = make_jwt(
        {
            "iss": cart_contents["merchant_name"],
            "sub": cart_contents["id"],
            "aud": "payment-processor",
            "iat": now,
            "exp": now + 900,  # 15 minutes
            "jti": str(uuid.uuid4()),
            "cart_hash": cart_hash,
        },
        merchant_private_key,
        kid=merchant_kid,
    )
    return {"contents": cart_contents, "merchant_authorization": authorization}


def build_payment_mandate(
    checkout_mandate: dict, user_private_key, user_kid: str
) -> dict:
    """Authorize payment, binding to the checkout via its signed-JWT hash."""
    now = int(datetime.now(UTC).timestamp())
    checkout_jwt = checkout_mandate["merchant_authorization"]
    checkout_hash = sha256_b64url(checkout_jwt.encode("ascii"))
    contents = {
        "payment_mandate_id": str(uuid.uuid4()),
        "payment_details_id": checkout_mandate["contents"]["payment_request"][
            "details"
        ]["id"],
        "merchant_agent": checkout_mandate["contents"]["merchant_name"],
        "timestamp": datetime.now(UTC).isoformat(),
    }
    payment_hash = sha256_b64url(canonical_json(contents))
    # In real AP2 this is an SD-JWT VP; here a plain JWT (see Lesson 03).
    authorization = make_jwt(
        {
            "iss": "user",
            "iat": now,
            "transaction_data": [checkout_hash, payment_hash],
        },
        user_private_key,
        kid=user_kid,
    )
    return {
        "payment_mandate_contents": contents,
        "user_authorization": authorization,
    }


def main() -> None:
    import json

    merchant_priv, _ = generate_p256_keypair()
    user_priv, _ = generate_p256_keypair()
    cart = build_cart_contents(
        cart_id="cart_123",
        merchant_name="Cat Store",
        item_label="Catnip Deluxe",
        amount=49.99,
        currency="USD",
        payment_request_id="pr_123",
        cart_expiry="2099-01-01T00:00:00Z",
    )
    checkout = build_checkout_mandate(cart, merchant_priv, "m-1")
    payment = build_payment_mandate(checkout, user_priv, "u-1")
    print("Checkout Mandate:\n", json.dumps(checkout, indent=2))
    print("\nPayment Mandate:\n", json.dumps(payment, indent=2))


if __name__ == "__main__":
    main()
