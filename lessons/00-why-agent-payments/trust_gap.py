"""Lesson 00 — Why agent payments need a protocol.

When an agent says "the user authorized this $50 purchase," what *proof* backs
that claim? Today: usually none. AP2's answer is "verifiable intent, not
inferred action" — a cryptographically signed mandate anyone can check.
"""
from __future__ import annotations

from ap2_shared.jose import make_jwt
from ap2_shared.keys import generate_p256_keypair


def unverifiable_claim() -> dict:
    """An agent asserting authority with nothing to back it up."""
    return {
        "agent_says": "The user authorized buying Catnip Deluxe for $49.99",
        "proof": None,
    }


def verifiable_claim(user_private_key, user_kid: str) -> dict:
    """The same intent, but signed by the user — anyone can verify it."""
    proof = make_jwt(
        {"intent": "buy Catnip Deluxe", "max_amount": 49.99, "currency": "USD"},
        user_private_key,
        kid=user_kid,
    )
    return {"agent_says": "The user authorized this purchase", "proof": proof}


def main() -> None:
    priv, _ = generate_p256_keypair()
    print("Without AP2:", unverifiable_claim())
    print("With AP2:   ", verifiable_claim(priv, "u-1"))


if __name__ == "__main__":
    main()
