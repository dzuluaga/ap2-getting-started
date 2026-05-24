from ap2_shared.jose import verify_jwt, sha256_b64url, canonical_json
from ap2_shared.keys import generate_p256_keypair

import build_mandate


def _sample_cart():
    return build_mandate.build_cart_contents(
        cart_id="cart_123",
        merchant_name="Cat Store",
        item_label="Catnip Deluxe",
        amount=49.99,
        currency="USD",
        payment_request_id="pr_123",
        cart_expiry="2099-01-01T00:00:00Z",
    )


def test_cart_contents_shape_matches_sdk_fields():
    cart = _sample_cart()
    assert cart["id"] == "cart_123"
    assert cart["merchant_name"] == "Cat Store"
    assert cart["payment_request"]["details"]["total"]["amount"]["value"] == 49.99
    assert cart["payment_request"]["details"]["total"]["amount"]["currency"] == "USD"


def test_checkout_mandate_is_a_signed_jwt_over_the_cart_hash():
    priv, pub = generate_p256_keypair()
    cart = _sample_cart()
    mandate = build_mandate.build_checkout_mandate(cart, priv, merchant_kid="m-1")
    payload = verify_jwt(mandate["merchant_authorization"], pub)
    assert payload is not None
    expected_hash = sha256_b64url(canonical_json(mandate["contents"]))
    assert payload["cart_hash"] == expected_hash
    assert payload["iss"] == "Cat Store"


def test_payment_mandate_links_to_the_checkout_mandate():
    merchant_priv, _ = generate_p256_keypair()
    user_priv, user_pub = generate_p256_keypair()
    cart = _sample_cart()
    checkout = build_mandate.build_checkout_mandate(cart, merchant_priv, "m-1")
    payment = build_mandate.build_payment_mandate(
        checkout, user_priv, user_kid="u-1"
    )
    payload = verify_jwt(payment["user_authorization"], user_pub)
    assert payload is not None
    checkout_hash = sha256_b64url(
        checkout["merchant_authorization"].encode("ascii")
    )
    assert checkout_hash in payload["transaction_data"]
    # Both bindings are committed: the checkout JWT and the payment contents.
    payment_hash = sha256_b64url(
        canonical_json(payment["payment_mandate_contents"])
    )
    assert payment_hash in payload["transaction_data"]
