"""Lesson 03 — Map the by-hand SD-JWT flow onto the official `ap2` SDK + the
AP2 ``OpenPaymentMandate`` pattern.

The SDK's ``MandateClient`` does exactly what Task 6/7 just built:
- ``create()`` signs a root SD-JWT (with ``cnf`` + selectively-disclosable
  constraints) — that is ``make_sdjwt`` in our shared module.
- ``present()`` appends a KB-style hop signed by the holder — that is
  ``make_kb_jwt`` + ``attach_kb``.
- ``verify()`` validates the issuer signature, the KB binding, and resolves
  disclosures — that is our ``verify``.

So our hand-built flow IS this, untyped. The lesson page also points out that
the SDK uses array-element selective disclosure (e.g. inside ``AllowedPayees``)
— a refinement we deliberately don't build by hand (out of scope, Lesson 04+).
"""
from __future__ import annotations

import json
import time

from cryptography.hazmat.primitives.asymmetric import ec
from jwcrypto.jwk import JWK

from ap2.sdk.mandate import MandateClient
from ap2.sdk.generated.open_payment_mandate import (
    AllowedPayees,
    AmountRange,
    OpenPaymentMandate,
)
from ap2.sdk.generated.payment_mandate import PaymentMandate
from ap2.sdk.generated.types.amount import Amount
from ap2.sdk.generated.types.merchant import Merchant
from ap2.sdk.generated.types.payment_instrument import PaymentInstrument


def _jwk_with_kid(raw_key, kid: str) -> JWK:
    d = json.loads(JWK.from_pyca(raw_key).export())
    d["kid"] = kid
    return JWK(**d)


def open_payment_mandate_flow():
    """Bank issues OpenPaymentMandate; agent presents closed PaymentMandate;
    merchant verifies. Mirrors the SDK README's canonical example."""
    issuer_jwk = _jwk_with_kid(
        ec.generate_private_key(ec.SECP256R1()), "bank-1"
    )
    agent_jwk = _jwk_with_kid(
        ec.generate_private_key(ec.SECP256R1()), "agent-1"
    )
    agent_pub = json.loads(agent_jwk.export_public())
    client = MandateClient()
    now = int(time.time())

    open_token = client.create(
        payloads=[
            OpenPaymentMandate(
                constraints=[
                    AmountRange(currency="USD", min=0, max=5000),
                    AllowedPayees(allowed=[Merchant(id="M-1", name="Cat Store")]),
                ],
                cnf={"jwk": agent_pub},
                iat=now,
                exp=now + 3600,
            )
        ],
        issuer_key=issuer_jwk,
    )

    chain = client.present(
        holder_key=agent_jwk,
        mandate_token=open_token,
        payloads=[
            PaymentMandate(
                transaction_id="tx_abc",
                payee=Merchant(id="M-1", name="Cat Store"),
                payment_amount=Amount(amount=2500, currency="USD"),
                payment_instrument=PaymentInstrument(
                    type="card", id="stub", description="Demo"
                ),
                iat=now,
                exp=now + 3600,
            )
        ],
        nonce="tx_abc",
        aud="merchant",
    )

    return client.verify(
        token=chain,
        key_or_provider=lambda token: issuer_jwk,
        expected_aud="merchant",
        expected_nonce="tx_abc",
    )


def main() -> None:
    payloads = open_payment_mandate_flow()
    print("AP2 SDK verified the OpenPaymentMandate → PaymentMandate flow.")
    print("Returned per-token payloads count:", len(payloads))


if __name__ == "__main__":
    main()
