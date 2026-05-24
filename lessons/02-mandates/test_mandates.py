from ap2_shared.jose import verify_jwt, sha256_b64url, canonical_json
from ap2_shared.keys import generate_p256_keypair

import build_mandate
import verify_mandate
import map_to_sdk


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


def test_valid_checkout_mandate_verifies():
    priv, pub = generate_p256_keypair()
    cart = _sample_cart()
    mandate = build_mandate.build_checkout_mandate(cart, priv, "m-1")
    assert verify_mandate.verify_checkout_mandate(mandate, pub) is True


def test_tampered_cart_fails_verification():
    priv, pub = generate_p256_keypair()
    cart = _sample_cart()
    mandate = build_mandate.build_checkout_mandate(cart, priv, "m-1")
    # Attacker lowers the price after the merchant signed the cart.
    mandate["contents"]["payment_request"]["details"]["total"]["amount"][
        "value"
    ] = 0.01
    assert verify_mandate.verify_checkout_mandate(mandate, pub) is False


def test_wrong_merchant_key_fails_verification():
    priv, _ = generate_p256_keypair()
    _, attacker_pub = generate_p256_keypair()
    cart = _sample_cart()
    mandate = build_mandate.build_checkout_mandate(cart, priv, "m-1")
    assert verify_mandate.verify_checkout_mandate(mandate, attacker_pub) is False


def test_sdk_cart_mandate_matches_hand_built_business_fields():
    merchant_priv, merchant_pub = generate_p256_keypair()
    cart = _sample_cart()
    hand = build_mandate.build_checkout_mandate(cart, merchant_priv, "m-1")

    sdk_cart = map_to_sdk.to_sdk_cart_mandate(
        cart, hand["merchant_authorization"]
    )
    assert sdk_cart.contents.id == hand["contents"]["id"]
    assert sdk_cart.contents.merchant_name == hand["contents"]["merchant_name"]
    assert (
        sdk_cart.contents.payment_request.details.total.amount.value
        == hand["contents"]["payment_request"]["details"]["total"]["amount"][
            "value"
        ]
    )
    # The SDK model carries our by-hand merchant JWT unchanged, and it still
    # verifies against the merchant's public key.
    assert sdk_cart.merchant_authorization == hand["merchant_authorization"]
    assert verify_mandate.verify_checkout_mandate(hand, merchant_pub) is True


def test_sdk_payment_mandate_builds():
    sdk_payment = map_to_sdk.to_sdk_payment_mandate(
        merchant_name="Cat Store",
        payment_request_id="pr_123",
        amount=49.99,
        currency="USD",
    )
    assert sdk_payment.payment_mandate_contents.merchant_agent == "Cat Store"
    assert (
        sdk_payment.payment_mandate_contents.payment_details_total.amount.value
        == 49.99
    )


def test_valid_payment_mandate_verifies():
    merchant_priv, _ = generate_p256_keypair()
    user_priv, user_pub = generate_p256_keypair()
    checkout = build_mandate.build_checkout_mandate(
        _sample_cart(), merchant_priv, "m-1"
    )
    payment = build_mandate.build_payment_mandate(checkout, user_priv, "u-1")
    assert (
        verify_mandate.verify_payment_mandate(payment, user_pub, checkout) is True
    )


def test_payment_mandate_wrong_user_key_fails():
    merchant_priv, _ = generate_p256_keypair()
    user_priv, _ = generate_p256_keypair()
    _, attacker_pub = generate_p256_keypair()
    checkout = build_mandate.build_checkout_mandate(
        _sample_cart(), merchant_priv, "m-1"
    )
    payment = build_mandate.build_payment_mandate(checkout, user_priv, "u-1")
    assert (
        verify_mandate.verify_payment_mandate(payment, attacker_pub, checkout)
        is False
    )


def test_tampered_payment_contents_fails():
    merchant_priv, _ = generate_p256_keypair()
    user_priv, user_pub = generate_p256_keypair()
    checkout = build_mandate.build_checkout_mandate(
        _sample_cart(), merchant_priv, "m-1"
    )
    payment = build_mandate.build_payment_mandate(checkout, user_priv, "u-1")
    # Tamper the payment contents after signing → payment_hash no longer matches.
    payment["payment_mandate_contents"]["merchant_agent"] = "Evil Store"
    assert (
        verify_mandate.verify_payment_mandate(payment, user_pub, checkout)
        is False
    )


def test_payment_mandate_not_bound_to_other_checkout_fails():
    merchant_priv, _ = generate_p256_keypair()
    user_priv, user_pub = generate_p256_keypair()
    checkout = build_mandate.build_checkout_mandate(
        _sample_cart(), merchant_priv, "m-1"
    )
    payment = build_mandate.build_payment_mandate(checkout, user_priv, "u-1")
    # A different checkout (unique JWT) breaks the binding even with same cart.
    other = build_mandate.build_checkout_mandate(
        _sample_cart(), merchant_priv, "m-1"
    )
    assert (
        verify_mandate.verify_payment_mandate(payment, user_pub, other) is False
    )
