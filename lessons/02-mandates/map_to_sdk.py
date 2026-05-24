"""Lesson 02 — Map the hand-built dicts onto the official `ap2` SDK models.

The SDK's stable data models (`ap2.models`) still name the merchant-signed cart
a `CartMandate`; the current spec/docs call it a "Checkout Mandate" — same idea,
terminology evolved. The SDK also has a newer SD-JWT "CheckoutMandate" chain
(`ap2.sdk`), which we reach in Lessons 03–04. Here we map to the classic models
to show our by-hand structure is the real thing, just spelled out.
"""
from __future__ import annotations

from ap2.models.mandate import (
    CartContents,
    CartMandate,
    PaymentMandate,
    PaymentMandateContents,
)
from ap2.models.payment_request import (
    PaymentCurrencyAmount,
    PaymentDetailsInit,
    PaymentItem,
    PaymentMethodData,
    PaymentRequest,
    PaymentResponse,
)


def to_sdk_cart_mandate(cart_contents: dict, merchant_authorization: str) -> CartMandate:
    """Translate our hand-built cart dict into the SDK's typed CartMandate."""
    details = cart_contents["payment_request"]["details"]
    total = details["total"]
    payment_request = PaymentRequest(
        method_data=[
            PaymentMethodData(
                supported_methods=md["supported_methods"],
                data=md.get("data", {}),
            )
            for md in cart_contents["payment_request"]["method_data"]
        ],
        details=PaymentDetailsInit(
            id=details["id"],
            display_items=[
                PaymentItem(
                    label=item["label"],
                    amount=PaymentCurrencyAmount(
                        currency=item["amount"]["currency"],
                        value=item["amount"]["value"],
                    ),
                )
                for item in details["display_items"]
            ],
            total=PaymentItem(
                label=total["label"],
                amount=PaymentCurrencyAmount(
                    currency=total["amount"]["currency"],
                    value=total["amount"]["value"],
                ),
            ),
        ),
    )
    contents = CartContents(
        id=cart_contents["id"],
        user_cart_confirmation_required=cart_contents[
            "user_cart_confirmation_required"
        ],
        payment_request=payment_request,
        cart_expiry=cart_contents["cart_expiry"],
        merchant_name=cart_contents["merchant_name"],
    )
    return CartMandate(
        contents=contents, merchant_authorization=merchant_authorization
    )


def to_sdk_payment_mandate(
    *, merchant_name: str, payment_request_id: str, amount: float, currency: str
) -> PaymentMandate:
    """Build the SDK's typed PaymentMandate from simple values."""
    contents = PaymentMandateContents(
        payment_mandate_id="pm_123",  # static demo id; real flows generate one
        payment_details_id=payment_request_id,
        payment_details_total=PaymentItem(
            label="Total",
            amount=PaymentCurrencyAmount(currency=currency, value=amount),
        ),
        payment_response=PaymentResponse(
            request_id=payment_request_id, method_name="card"
        ),
        merchant_agent=merchant_name,
    )
    # user_authorization is the SD-JWT VP in real AP2 (Lesson 03); omit here.
    return PaymentMandate(payment_mandate_contents=contents)


def main() -> None:
    import build_mandate
    from ap2_shared.keys import generate_p256_keypair

    priv, _ = generate_p256_keypair()
    cart = build_mandate.build_cart_contents(
        cart_id="cart_123",
        merchant_name="Cat Store",
        item_label="Catnip Deluxe",
        amount=49.99,
        currency="USD",
        payment_request_id="pr_123",
        cart_expiry="2099-01-01T00:00:00Z",
    )
    hand = build_mandate.build_checkout_mandate(cart, priv, "m-1")
    sdk_cart = to_sdk_cart_mandate(cart, hand["merchant_authorization"])
    print("SDK CartMandate:\n", sdk_cart.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
