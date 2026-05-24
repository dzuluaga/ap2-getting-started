"""Lesson 01 — The cast and the two journeys.

Six roles cooperate in an AP2 transaction, and there are two core journeys:
Human-Present (the user is available to approve) and Human-Not-Present (the
user pre-authorizes constraints and the agent acts later).
"""
from __future__ import annotations

ROLES: dict[str, str] = {
    "Shopping Agent": "Finds products, builds the checkout, executes the purchase.",
    "Credential Provider": "Holds the user's payment credentials (the wallet).",
    "Merchant": "Owns the catalog; signs the cart; fulfills the order.",
    "Merchant Payment Processor": "Submits the transaction for authorization.",
    "Trusted Surface": "Non-agentic UI that captures the user's signed consent.",
    "Network / Issuer": "Runs the payment rails; issues credentials; authorizes.",
}


def human_present_steps() -> list[str]:
    return [
        "User gives the Shopping Agent a task.",
        "Shopping Agent assembles a cart with the Merchant.",
        "Merchant signs the cart (the Checkout Mandate).",
        "Trusted Surface shows the cart; user signs to approve.",
        "Payment Mandate is shared with the Network/Issuer; payment executes.",
    ]


def human_not_present_steps() -> list[str]:
    return [
        "User approves constraints up front (e.g. 'buy when price < $100').",
        "This is an OPEN Checkout Mandate — not yet bound to a specific cart.",
        "Shopping Agent waits until the constraints are satisfied.",
        "Once a matching cart exists, the mandate is CLOSED and payment runs.",
    ]


def main() -> None:
    print("Roles:")
    for name, duty in ROLES.items():
        print(f"  - {name}: {duty}")
    print("\nHuman-Present:")
    for step in human_present_steps():
        print(f"  · {step}")
    print("\nHuman-Not-Present:")
    for step in human_not_present_steps():
        print(f"  · {step}")


if __name__ == "__main__":
    main()
