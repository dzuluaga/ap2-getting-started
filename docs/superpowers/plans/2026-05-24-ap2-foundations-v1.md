# AP2 Foundations (v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first publishable milestone of the "AP2 from First Principles" learning resource — a Docusaurus site (deployed to Vercel) teaching Lessons 00–02, backed by runnable, tested Python that builds AP2 mandates by hand and maps them to the official `ap2` SDK.

**Architecture:** Monorepo, code-as-source-of-truth. Runnable lesson code lives in `lessons/NN-slug/` and a shared, installable `ap2_shared` package; the Docusaurus site in `site/` imports the *real* code into lesson pages via `remark-code-import`, so every published snippet is tested code. Each lesson follows a fixed five-beat spine (Frame · Build · Map · Inspect · Check).

**Tech Stack:** Python 3.11+ with `uv`; `cryptography` (from-scratch ES256/JWT) + the git-installed official `ap2` SDK (the "map" target); Docusaurus + TypeScript + `remark-code-import`; deployed to Vercel.

**Deviation from spec (intentional):** the spec sketched shared helpers at `lessons/_shared/`. Numbered lesson dirs (`02-mandates`) are not importable Python packages, so shared code lives in a top-level **installable** package `ap2_shared/` instead. Everything else matches `docs/superpowers/specs/2026-05-24-ap2-from-first-principles-design.md`.

**Reference (read-only):** the official AP2 repo is cloned at `/Users/diegozuluaga/tools/git/AP2`. Useful files: `code/sdk/python/ap2/models/mandate.py`, `.../models/payment_request.py`, `code/sdk/python/ap2/sdk/README.md`, `docs/overview.md`, `docs/glossary.md`.

---

## File Structure

Created in this plan:

```
ap2-getting-started/
├── pyproject.toml              # uv project; deps: ap2 (git), pytest (dev)
├── uv.lock                     # committed for reproducibility (pins ap2 commit)
├── .gitignore
├── README.md                   # what this is, how to run, live link
├── vercel.json                 # monorepo build of site/
├── ap2_shared/                 # installable shared package (importable everywhere)
│   ├── __init__.py
│   ├── jose.py                 # b64url, canonical_json, sha256, ES256 sign/verify, make_jwt/verify_jwt
│   ├── keys.py                 # generate_p256_keypair()
│   └── test_jose.py            # unit tests for the primitives
├── lessons/
│   ├── _template/              # lesson skeleton copied by scripts/new-lesson.py
│   │   ├── README.md
│   │   ├── example.py
│   │   ├── test_example.py
│   │   └── run.sh
│   ├── 00-why-agent-payments/
│   │   ├── README.md
│   │   ├── trust_gap.py
│   │   └── test_trust_gap.py
│   ├── 01-roles-and-journeys/
│   │   ├── README.md
│   │   ├── roles.py
│   │   └── test_roles.py
│   └── 02-mandates/
│       ├── README.md
│       ├── build_mandate.py
│       ├── verify_mandate.py
│       ├── map_to_sdk.py
│       ├── test_mandates.py
│       └── run.sh
├── scripts/
│   └── new-lesson.py           # scaffold a new lesson from _template
└── site/                       # Docusaurus (TypeScript) — scaffolded in Task 9
    ├── docusaurus.config.ts
    ├── sidebars.ts
    ├── package.json
    ├── docs/
    │   ├── 00-why-agent-payments.mdx
    │   ├── 01-roles-and-journeys.mdx
    │   └── 02-mandates.mdx
    ├── blog/
    │   └── 2026-05-24-learning-ap2-from-first-principles.md
    └── src/
        ├── components/Term/index.tsx
        ├── data/glossary.ts
        └── pages/
            ├── index.tsx       # landing
            ├── glossary.tsx
            └── roadmap.tsx
```

---

## Task 1: Python workspace + official `ap2` SDK installed

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "ap2-getting-started"
version = "0.1.0"
description = "Learn the Agent Payments Protocol (AP2) from first principles."
requires-python = ">=3.11"
dependencies = [
    "ap2",
]

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.uv.sources]
ap2 = { git = "https://github.com/google-agentic-commerce/ap2.git" }

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["ap2_shared*"]

[tool.pytest.ini_options]
testpaths = ["ap2_shared", "lessons"]
python_files = ["test_*.py"]
addopts = "-q"
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
# Python
.venv/
__pycache__/
*.pyc
.pytest_cache/
.env

# Node / Docusaurus
node_modules/
site/build/
site/.docusaurus/
npm-debug.log*
```

- [ ] **Step 3: Create the package dir so the build target exists**

Run: `mkdir -p ap2_shared && printf '"""Shared helpers for AP2 lessons."""\n' > ap2_shared/__init__.py`

- [ ] **Step 4: Sync the environment (installs `ap2` from git + dev deps)**

Run: `uv sync --extra dev`
Expected: resolves and builds `ap2` from GitHub, writes `uv.lock`. If the git build fails (e.g., offline), use the local clone as a fallback source and re-run:
`uv pip install -e /Users/diegozuluaga/tools/git/AP2` then `uv sync --extra dev`.

- [ ] **Step 5: Verify the SDK imports**

Run: `uv run python -c "import ap2; from ap2.models.mandate import CartMandate, PaymentMandate; print('ap2 OK')"`
Expected: prints `ap2 OK`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore uv.lock ap2_shared/__init__.py
git commit -m "chore: python workspace with official ap2 SDK (git)"
```

---

## Task 2: `ap2_shared` JOSE primitives (ES256 / JWT by hand)

These primitives are written from scratch on top of `cryptography` so lessons can *show* what a JWT is (base64url header.payload.signature, ES256 with raw R‖S JOSE encoding). Reused by every code lesson.

**Files:**
- Create: `ap2_shared/jose.py`
- Create: `ap2_shared/keys.py`
- Test: `ap2_shared/test_jose.py`

- [ ] **Step 1: Write the failing tests**

`ap2_shared/test_jose.py`:

```python
from ap2_shared.jose import (
    b64url_encode, b64url_decode, canonical_json, sha256_b64url,
    make_jwt, verify_jwt, decode_jwt_unverified,
)
from ap2_shared.keys import generate_p256_keypair


def test_b64url_roundtrip_no_padding():
    s = b64url_encode(b"hello?>")
    assert "=" not in s
    assert b64url_decode(s) == b"hello?>"


def test_canonical_json_is_sorted_and_compact():
    assert canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def test_sha256_b64url_is_stable():
    assert sha256_b64url(b"abc") == sha256_b64url(b"abc")
    assert sha256_b64url(b"abc") != sha256_b64url(b"abd")


def test_jwt_sign_and_verify_roundtrip():
    priv, pub = generate_p256_keypair()
    token = make_jwt({"iss": "merchant", "amount": 4999}, priv, kid="m-1")
    payload = verify_jwt(token, pub)
    assert payload is not None
    assert payload["iss"] == "merchant"
    assert decode_jwt_unverified(token)["amount"] == 4999


def test_verify_fails_on_tampered_signature():
    priv, pub = generate_p256_keypair()
    token = make_jwt({"iss": "merchant"}, priv, kid="m-1")
    head, body, sig = token.split(".")
    flipped = sig[:-2] + ("AA" if sig[-2:] != "AA" else "BB")
    assert verify_jwt(f"{head}.{body}.{flipped}", pub) is None


def test_verify_fails_with_wrong_key():
    priv, _ = generate_p256_keypair()
    _, other_pub = generate_p256_keypair()
    token = make_jwt({"iss": "merchant"}, priv, kid="m-1")
    assert verify_jwt(token, other_pub) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest ap2_shared/test_jose.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'ap2_shared.jose'`

- [ ] **Step 3: Implement `ap2_shared/keys.py`**

```python
"""EC P-256 keypair generation for AP2 lessons."""
from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import ec


def generate_p256_keypair():
    """Return (private_key, public_key) on the NIST P-256 curve (ES256)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()
```

- [ ] **Step 4: Implement `ap2_shared/jose.py`**

```python
"""Minimal, from-scratch JOSE primitives (base64url, JSON canonicalization,
SHA-256, and ES256 JWTs) built directly on `cryptography`.

The point is pedagogical: a JWT is just
`base64url(header) . base64url(payload) . base64url(signature)`, where the
signature is ES256 over the first two segments. JOSE uses the raw R‖S
signature form (64 bytes), not ASN.1/DER — we convert explicitly so the
mechanic is visible.
"""
from __future__ import annotations

import base64
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def canonical_json(obj: Any) -> bytes:
    """Deterministic JSON: sorted keys, no whitespace. Used for hashing."""
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sha256_b64url(data: bytes) -> str:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(data)
    return b64url_encode(digest.finalize())


def _es256_sign(signing_input: bytes, private_key) -> bytes:
    der = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def _es256_verify(signing_input: bytes, raw_sig: bytes, public_key) -> bool:
    if len(raw_sig) != 64:
        return False
    r = int.from_bytes(raw_sig[:32], "big")
    s = int.from_bytes(raw_sig[32:], "big")
    try:
        public_key.verify(
            encode_dss_signature(r, s), signing_input, ec.ECDSA(hashes.SHA256())
        )
        return True
    except InvalidSignature:
        return False


def make_jwt(payload: dict, private_key, kid: str) -> str:
    """Build a compact ES256 JWT from a payload dict."""
    header = {"alg": "ES256", "typ": "JWT", "kid": kid}
    encoded_header = b64url_encode(canonical_json(header))
    encoded_payload = b64url_encode(canonical_json(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = b64url_encode(_es256_sign(signing_input, private_key))
    return f"{encoded_header}.{encoded_payload}.{signature}"


def verify_jwt(token: str, public_key) -> dict | None:
    """Return the payload if the signature is valid, else None."""
    try:
        encoded_header, encoded_payload, encoded_sig = token.split(".")
    except ValueError:
        return None
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    if not _es256_verify(signing_input, b64url_decode(encoded_sig), public_key):
        return None
    return json.loads(b64url_decode(encoded_payload))


def decode_jwt_unverified(token: str) -> dict:
    """Decode the payload WITHOUT checking the signature (for inspection)."""
    _, encoded_payload, _ = token.split(".")
    return json.loads(b64url_decode(encoded_payload))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest ap2_shared/test_jose.py -q`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add ap2_shared/jose.py ap2_shared/keys.py ap2_shared/test_jose.py
git commit -m "feat(shared): from-scratch ES256 JWT primitives + tests"
```

---

## Task 3: Lesson 02 — build mandates by hand

Builds the Checkout (cart) mandate as a merchant-signed **plain JWT** over a hash of the cart, plus a Payment mandate. SD-JWT selective disclosure is deferred to Lesson 03.

**Files:**
- Create: `lessons/02-mandates/build_mandate.py`
- Test: `lessons/02-mandates/test_mandates.py` (created here; extended in Tasks 4–5)

- [ ] **Step 1: Write the failing tests**

`lessons/02-mandates/test_mandates.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest lessons/02-mandates/test_mandates.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'build_mandate'`

- [ ] **Step 3: Implement `lessons/02-mandates/build_mandate.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest lessons/02-mandates/test_mandates.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the demo**

Run: `uv run python lessons/02-mandates/build_mandate.py`
Expected: prints a Checkout Mandate and Payment Mandate as JSON.

- [ ] **Step 6: Commit**

```bash
git add lessons/02-mandates/build_mandate.py lessons/02-mandates/test_mandates.py
git commit -m "feat(lesson-02): build checkout + payment mandates by hand"
```

---

## Task 4: Lesson 02 — verify mandates + tamper detection

**Files:**
- Create: `lessons/02-mandates/verify_mandate.py`
- Modify: `lessons/02-mandates/test_mandates.py` (append tests)

- [ ] **Step 1: Append failing tests to `test_mandates.py`**

```python
import verify_mandate


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
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest lessons/02-mandates/test_mandates.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'verify_mandate'`

- [ ] **Step 3: Implement `lessons/02-mandates/verify_mandate.py`**

```python
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
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest lessons/02-mandates/test_mandates.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Run the demo**

Run: `uv run python lessons/02-mandates/verify_mandate.py`
Expected: `Valid mandate verifies: True` then `Tampered mandate verifies: False (expected False)`

- [ ] **Step 6: Commit**

```bash
git add lessons/02-mandates/verify_mandate.py lessons/02-mandates/test_mandates.py
git commit -m "feat(lesson-02): verify mandates + detect cart tampering"
```

---

## Task 5: Lesson 02 — map hand-built mandates to the official `ap2` SDK

**Files:**
- Create: `lessons/02-mandates/map_to_sdk.py`
- Modify: `lessons/02-mandates/test_mandates.py` (append tests)

- [ ] **Step 1: Append failing tests to `test_mandates.py`**

```python
import map_to_sdk


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
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest lessons/02-mandates/test_mandates.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'map_to_sdk'`

- [ ] **Step 3: Implement `lessons/02-mandates/map_to_sdk.py`**

```python
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
    details = cart_contents["payment_request"]["details"]
    total = details["total"]
    item = details["display_items"][0]
    payment_request = PaymentRequest(
        method_data=[PaymentMethodData(supported_methods="card", data={})],
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
    contents = PaymentMandateContents(
        payment_mandate_id="pm_123",
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
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest lessons/02-mandates/test_mandates.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Run the demo**

Run: `uv run python lessons/02-mandates/map_to_sdk.py`
Expected: prints an `ap2.models.mandate.CartMandate` serialized as JSON.

- [ ] **Step 6: Commit**

```bash
git add lessons/02-mandates/map_to_sdk.py lessons/02-mandates/test_mandates.py
git commit -m "feat(lesson-02): map hand-built mandates onto official ap2 SDK"
```

---

## Task 6: Lesson 02 — `run.sh` + lesson README

**Files:**
- Create: `lessons/02-mandates/run.sh`
- Create: `lessons/02-mandates/README.md`

- [ ] **Step 1: Create `lessons/02-mandates/run.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo root
echo "== build ==";  uv run python lessons/02-mandates/build_mandate.py
echo; echo "== verify =="; uv run python lessons/02-mandates/verify_mandate.py
echo; echo "== map ==";    uv run python lessons/02-mandates/map_to_sdk.py
```

- [ ] **Step 2: Make it executable and run it**

Run: `chmod +x lessons/02-mandates/run.sh && bash lessons/02-mandates/run.sh`
Expected: runs all three scripts; verify section prints `True` then `False`.

- [ ] **Step 3: Create `lessons/02-mandates/README.md`**

```markdown
# Lesson 02 — Mandates, the unit of trust

Build a **Checkout Mandate** and a **Payment Mandate** by hand, then map them to
the official `ap2` SDK models.

## Run

```bash
bash run.sh            # build → verify → map
uv run pytest lessons/02-mandates -q
```

## Files
- `build_mandate.py` — build the mandates (merchant-signed cart as a plain JWT).
- `verify_mandate.py` — verify the signature **and** the cart hash (tamper test).
- `map_to_sdk.py` — the same data as `ap2.models.mandate.CartMandate` / `PaymentMandate`.

The full narrative lives on the site: **/docs/mandates**.
```

- [ ] **Step 4: Commit**

```bash
git add lessons/02-mandates/run.sh lessons/02-mandates/README.md
git commit -m "docs(lesson-02): run.sh + lesson README"
```

---

## Task 7: Lessons 00 and 01 — runnable illustrations

Tiny, runnable scripts so every lesson honors the "Build" beat.

**Files:**
- Create: `lessons/00-why-agent-payments/trust_gap.py`, `test_trust_gap.py`, `README.md`
- Create: `lessons/01-roles-and-journeys/roles.py`, `test_roles.py`, `README.md`

- [ ] **Step 1: Write failing test `lessons/00-why-agent-payments/test_trust_gap.py`**

```python
from ap2_shared.jose import verify_jwt
from ap2_shared.keys import generate_p256_keypair

import trust_gap


def test_unverifiable_claim_has_no_proof():
    claim = trust_gap.unverifiable_claim()
    assert claim["proof"] is None


def test_verifiable_claim_is_signed_and_checks_out():
    priv, pub = generate_p256_keypair()
    claim = trust_gap.verifiable_claim(priv, "u-1")
    assert verify_jwt(claim["proof"], pub) is not None
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest lessons/00-why-agent-payments -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'trust_gap'`

- [ ] **Step 3: Implement `lessons/00-why-agent-payments/trust_gap.py`**

```python
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
```

- [ ] **Step 4: Write failing test `lessons/01-roles-and-journeys/test_roles.py`**

```python
import roles


def test_six_roles_are_defined():
    assert len(roles.ROLES) == 6
    assert "Shopping Agent" in roles.ROLES


def test_human_present_signs_a_checkout_mandate():
    steps = roles.human_present_steps()
    assert any("Checkout Mandate" in s for s in steps)


def test_human_not_present_uses_open_then_closed_mandate():
    steps = roles.human_not_present_steps()
    joined = " ".join(steps).lower()
    assert "open" in joined and "closed" in joined
```

- [ ] **Step 5: Run to verify both lesson test files fail appropriately**

Run: `uv run pytest lessons/01-roles-and-journeys -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'roles'`

- [ ] **Step 6: Implement `lessons/01-roles-and-journeys/roles.py`**

```python
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
```

- [ ] **Step 7: Run all lesson tests to verify they pass**

Run: `uv run pytest lessons -q`
Expected: PASS (all lesson tests green)

- [ ] **Step 8: Create the two lesson READMEs**

`lessons/00-why-agent-payments/README.md`:

```markdown
# Lesson 00 — Why agent payments?

`trust_gap.py` contrasts an agent's *unverifiable* claim of authority with a
*verifiable* (signed) one — the core idea behind AP2's "verifiable intent."

Run: `uv run python lessons/00-why-agent-payments/trust_gap.py`
```

`lessons/01-roles-and-journeys/README.md`:

```markdown
# Lesson 01 — The cast and the journeys

`roles.py` lists the six AP2 roles and walks the Human-Present vs
Human-Not-Present journeys (Open → Closed mandate).

Run: `uv run python lessons/01-roles-and-journeys/roles.py`
```

- [ ] **Step 9: Commit**

```bash
git add lessons/00-why-agent-payments lessons/01-roles-and-journeys
git commit -m "feat(lessons 00-01): runnable trust-gap and roles illustrations"
```

---

## Task 8: Lesson scaffold (`_template` + `scripts/new-lesson.py`)

**Files:**
- Create: `lessons/_template/README.md`, `example.py`, `test_example.py`, `run.sh`
- Create: `scripts/new-lesson.py`
- Test: `scripts/test_new_lesson.py`

- [ ] **Step 1: Create the `_template` files**

`lessons/_template/README.md`:

```markdown
# Lesson NN — <title>

> Five-beat spine: Frame · Build · Map · Inspect · Check.

## Build
`example.py` — replace with this lesson's from-scratch code.

Run: `uv run python lessons/NN-<slug>/example.py`
Test: `uv run pytest lessons/NN-<slug> -q`
```

`lessons/_template/example.py`:

```python
"""Lesson NN — <title>. Replace with the from-scratch build."""


def demo() -> str:
    return "replace me"


if __name__ == "__main__":
    print(demo())
```

`lessons/_template/test_example.py`:

```python
import example


def test_demo_runs():
    assert isinstance(example.demo(), str)
```

`lessons/_template/run.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
uv run python lessons/_template/example.py
```

- [ ] **Step 2: Write failing test `scripts/test_new_lesson.py`**

```python
import subprocess
import sys
from pathlib import Path


def test_new_lesson_creates_a_folder(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    dest = tmp_path / "lessons"
    dest.mkdir()
    (dest / "_template").mkdir()
    (dest / "_template" / "example.py").write_text("print('x')\n")
    subprocess.run(
        [sys.executable, str(repo / "scripts" / "new-lesson.py"),
         "03", "selective-disclosure", "--lessons-dir", str(dest)],
        check=True,
    )
    assert (dest / "03-selective-disclosure" / "example.py").exists()
```

- [ ] **Step 3: Run to verify it fails**

Run: `uv run pytest scripts/test_new_lesson.py -q`
Expected: FAIL (script does not exist yet → non-zero exit / FileNotFound)

- [ ] **Step 4: Implement `scripts/new-lesson.py`**

```python
"""Scaffold a new lesson folder from lessons/_template.

Usage: python scripts/new-lesson.py <number> <slug> [--lessons-dir DIR]
Example: python scripts/new-lesson.py 03 selective-disclosure
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("number", help="Two-digit lesson number, e.g. 03")
    parser.add_argument("slug", help="kebab-case slug, e.g. selective-disclosure")
    parser.add_argument(
        "--lessons-dir",
        default=str(Path(__file__).resolve().parents[1] / "lessons"),
    )
    args = parser.parse_args()

    lessons_dir = Path(args.lessons_dir)
    template = lessons_dir / "_template"
    dest = lessons_dir / f"{args.number}-{args.slug}"
    if dest.exists():
        raise SystemExit(f"{dest} already exists")
    shutil.copytree(template, dest)
    print(f"Created {dest}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest scripts/test_new_lesson.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
chmod +x lessons/_template/run.sh
git add lessons/_template scripts/new-lesson.py scripts/test_new_lesson.py
git commit -m "feat(scaffold): lesson _template + new-lesson.py generator"
```

---

## Task 9: Scaffold the Docusaurus site

**Files:**
- Create: `site/` (Docusaurus classic + TypeScript)
- Modify: `site/docusaurus.config.ts`
- Add dep: `remark-code-import`

- [ ] **Step 1: Scaffold**

Run: `npx create-docusaurus@latest site classic --typescript`
Expected: creates `site/` with a working classic theme.

- [ ] **Step 2: Install the code-import plugin**

Run: `cd site && npm install remark-code-import && cd ..`

- [ ] **Step 3: Replace `site/docusaurus.config.ts`**

```ts
import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';
import codeImport from 'remark-code-import';
import path from 'path';

const config: Config = {
  title: 'AP2 from First Principles',
  tagline: 'Learn the Agent Payments Protocol by building it, then mapping to the SDK.',
  favicon: 'img/favicon.ico',
  url: 'https://ap2-getting-started.vercel.app',
  baseUrl: '/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  i18n: {defaultLocale: 'en', locales: ['en']},
  presets: [
    [
      'classic',
      {
        docs: {
          routeBasePath: 'docs',
          sidebarPath: './sidebars.ts',
          remarkPlugins: [
            [
              codeImport,
              {
                allowImportingFromOutside: true,
                rootDir: path.resolve(__dirname, '..'),
              },
            ],
          ],
        },
        blog: {showReadingTime: true},
        theme: {customCss: './src/css/custom.css'},
      } satisfies Preset.Options,
    ],
  ],
  themeConfig: {
    navbar: {
      title: 'AP2 from First Principles',
      items: [
        {type: 'docSidebar', sidebarId: 'lessons', position: 'left', label: 'Lessons'},
        {to: '/roadmap', label: 'Roadmap', position: 'left'},
        {to: '/glossary', label: 'Glossary', position: 'left'},
        {to: '/blog', label: 'Blog', position: 'left'},
        {
          href: 'https://github.com/google-agentic-commerce/AP2',
          label: 'AP2 spec',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Learn',
          items: [
            {label: 'Lessons', to: '/docs/why-agent-payments'},
            {label: 'Roadmap', to: '/roadmap'},
            {label: 'Glossary', to: '/glossary'},
          ],
        },
        {
          title: 'AP2',
          items: [
            {label: 'Official repo', href: 'https://github.com/google-agentic-commerce/AP2'},
            {label: 'Intro video', href: 'https://youtu.be/jSHj0z9Gi24'},
          ],
        },
      ],
      copyright: `Built ${new Date().getFullYear()} as a public learning resource.`,
    },
    prism: {theme: prismThemes.github, darkTheme: prismThemes.dracula},
  } satisfies Preset.ThemeConfig,
};

export default config;
```

- [ ] **Step 4: Remove the default tutorial docs and blog samples**

Run: `rm -rf site/docs/* site/blog/* && rm -rf "site/docs/tutorial-basics" "site/docs/tutorial-extras" 2>/dev/null; true`

- [ ] **Step 5: Verify the site still builds (with empty docs it will warn; we add content next)**

Run: `cd site && npm run build && cd ..`
Expected: build may fail only due to missing docs/pages we add in later tasks. If it fails solely on broken links to not-yet-created pages, proceed — Task 14 runs the authoritative full build. (Do not weaken `onBrokenLinks`.)

- [ ] **Step 6: Commit**

```bash
git add site
git commit -m "chore(site): scaffold Docusaurus + remark-code-import config"
```

---

## Task 10: Glossary data, page, and `<Term>` tooltip

**Files:**
- Create: `site/src/data/glossary.ts`
- Create: `site/src/pages/glossary.tsx`
- Create: `site/src/components/Term/index.tsx`

- [ ] **Step 1: Create `site/src/data/glossary.ts`**

```ts
export type GlossaryEntry = {
  id: string;
  term: string;
  acronym?: string;
  short: string;   // plain-English gloss
  spec: string;    // closer to the official definition
};

export const glossary: GlossaryEntry[] = [
  {id: 'ap2', term: 'Agent Payments Protocol', acronym: 'AP2',
   short: 'An open protocol that lets AI agents complete payments with verifiable authority.',
   spec: 'An open protocol designed to enable AI agents to securely interoperate and complete payments autonomously.'},
  {id: 'shopping-agent', term: 'Shopping Agent', acronym: 'SA',
   short: 'The agent that talks to the user, finds products, and drives the purchase.',
   spec: 'The primary agent performing product discovery, building the checkout, and executing the purchase.'},
  {id: 'credential-provider', term: 'Credential Provider', acronym: 'CP',
   short: "The user's wallet — holds and releases payment credentials.",
   spec: "A secure entity, like a digital wallet, responsible for managing and executing the user's payment and identity credentials."},
  {id: 'merchant', term: 'Merchant', acronym: 'M',
   short: 'Owns the catalog, signs the cart, and fulfills the order.',
   spec: 'The source of the Checkout; owns the catalog and fulfills orders.'},
  {id: 'merchant-payment-processor', term: 'Merchant Payment Processor', acronym: 'MPP',
   short: 'Submits the transaction into the payment ecosystem for authorization.',
   spec: 'Responsible for processing payments and verifying the Payment Credential is authorized to pay for this Checkout.'},
  {id: 'trusted-surface', term: 'Trusted Surface', acronym: 'TS',
   short: 'A non-agentic UI where the user gives informed, signed consent.',
   spec: 'A secure, non-agentic interface that renders Mandate Content to the user for authorization and consent.'},
  {id: 'mandate', term: 'Mandate',
   short: 'Signed, hash-bound intent — the unit of trust in AP2.',
   spec: 'A signed authorization created when a user (or merchant) consents to an action.'},
  {id: 'checkout-mandate', term: 'Checkout Mandate',
   short: 'Authorizes completing a specific checkout; the merchant signs the cart.',
   spec: 'A Mandate used for authorizing the completion of a checkout.'},
  {id: 'payment-mandate', term: 'Payment Mandate',
   short: 'Authorizes the payment for a checkout; shared with network/issuer for trust.',
   spec: 'A Mandate used for authorizing the payment for a particular checkout.'},
  {id: 'open-mandate', term: 'Open Mandate',
   short: 'A mandate not yet bound to a specific action; carries constraints.',
   spec: "A Mandate not yet bound to a particular action; carries constraints applied to a closed mandate."},
  {id: 'closed-mandate', term: 'Closed Mandate',
   short: 'A mandate bound to a specific action with a verifier.',
   spec: 'A Mandate bound to a particular action with a Verifier to authorize the agent.'},
  {id: 'mandate-receipt', term: 'Mandate Receipt',
   short: 'A verifier-signed token recording the result of an authorization.',
   spec: 'A Verifier-signed JWT indicating the result of the action authorization.'},
  {id: 'verifiable-intent', term: 'Verifiable Intent',
   short: 'Trust based on signed proof, not on guessing what an LLM meant.',
   spec: 'Transactions anchored to deterministic, non-repudiable proof of intent from all parties.'},
  {id: 'selective-disclosure', term: 'Selective Disclosure',
   short: 'Reveal only the fields each party needs — keeps PCI/private data minimal.',
   spec: 'Mechanism (via SD-JWT) preventing shopping-side agents from seeing sensitive payment data.'},
  {id: 'sd-jwt', term: 'SD-JWT',
   short: 'A JWT that supports selectively disclosing individual claims.',
   spec: 'Selective Disclosure JWT; basis for AP2 mandates with key binding (KB-JWT).'},
  {id: 'human-present', term: 'Human-Present', acronym: 'HP',
   short: 'The user is available to approve the payment in the moment.',
   spec: 'A journey where the human is available when the payment must be authorized.'},
  {id: 'human-not-present', term: 'Human-Not-Present', acronym: 'HNP',
   short: 'The user pre-authorizes constraints; the agent acts later on their behalf.',
   spec: 'A journey where the agent proceeds with payment in the user’s absence under pre-approved conditions.'},
  {id: 'a2a', term: 'Agent2Agent Protocol', acronym: 'A2A',
   short: 'Standard for agents to talk to each other; AP2 can extend it.',
   spec: 'An open standard for secure communication and task management between AI agents.'},
  {id: 'sca', term: 'Strong Customer Authentication', acronym: 'SCA',
   short: 'Regulatory requirement to strongly authenticate and link a transaction.',
   spec: 'A process required by regulatory frameworks for online identification and transaction initiation.'},
];
```

- [ ] **Step 2: Create `site/src/pages/glossary.tsx`**

```tsx
import React from 'react';
import Layout from '@theme/Layout';
import {glossary} from '@site/src/data/glossary';

export default function Glossary(): JSX.Element {
  const sorted = [...glossary].sort((a, b) => a.term.localeCompare(b.term));
  return (
    <Layout title="Glossary" description="AP2 terminology">
      <main className="container margin-vert--lg">
        <h1>AP2 Glossary</h1>
        <p>The vocabulary used across the lessons. Say it like you mean it.</p>
        <table>
          <thead>
            <tr><th>Term</th><th>Plain English</th><th>Closer to spec</th></tr>
          </thead>
          <tbody>
            {sorted.map((e) => (
              <tr key={e.id} id={e.id}>
                <td><strong>{e.term}</strong>{e.acronym ? ` (${e.acronym})` : ''}</td>
                <td>{e.short}</td>
                <td>{e.spec}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </main>
    </Layout>
  );
}
```

- [ ] **Step 3: Create `site/src/components/Term/index.tsx`**

```tsx
import React from 'react';
import {glossary} from '@site/src/data/glossary';

export default function Term({id, children}: {id: string; children: React.ReactNode}): JSX.Element {
  const entry = glossary.find((e) => e.id === id);
  return (
    <a href={`/glossary#${id}`} title={entry ? entry.short : id}
       style={{textDecoration: 'underline dotted', cursor: 'help'}}>
      {children}
    </a>
  );
}
```

- [ ] **Step 4: Verify the glossary page builds**

Run: `cd site && npm run build 2>&1 | tail -20 && cd ..`
Expected: no errors referencing `glossary.tsx` or `glossary.ts` (link warnings for not-yet-created lesson pages are acceptable until Task 14).

- [ ] **Step 5: Commit**

```bash
git add site/src/data/glossary.ts site/src/pages/glossary.tsx site/src/components/Term
git commit -m "feat(site): glossary data, page, and Term tooltip"
```

---

## Task 11: Roadmap page + landing page

**Files:**
- Create: `site/src/pages/roadmap.tsx`
- Modify: `site/src/pages/index.tsx`

- [ ] **Step 1: Create `site/src/pages/roadmap.tsx`**

```tsx
import React from 'react';
import Layout from '@theme/Layout';

type Lesson = {n: string; title: string; v1: boolean};

const lessons: Lesson[] = [
  {n: '00', title: 'Why agent payments?', v1: true},
  {n: '01', title: 'The cast & the journeys', v1: true},
  {n: '02', title: 'Mandates, the unit of trust', v1: true},
  {n: '03', title: 'Selective disclosure: SD-JWT & key binding', v1: false},
  {n: '04', title: 'Mandate chains & receipts; SCA & dynamic linking', v1: false},
  {n: '05', title: 'Human-Present happy path, end-to-end', v1: false},
  {n: '06', title: 'Human-Not-Present & autonomous delegation', v1: false},
  {n: '07', title: 'Riding on A2A', v1: false},
  {n: '08', title: 'AP2 with MCP, UCP, and x402', v1: false},
  {n: '09', title: 'Action authorization, disputes & liability', v1: false},
];

export default function Roadmap(): JSX.Element {
  return (
    <Layout title="Roadmap" description="The AP2 learning path">
      <main className="container margin-vert--lg">
        <h1>Roadmap</h1>
        <p>Lessons ship incrementally. v1 covers the foundations (00–02).</p>
        <ul>
          {lessons.map((l) => (
            <li key={l.n}>
              <strong>{l.n}</strong> — {l.title}{' '}
              {l.v1 ? <span>✅ available</span> : <em>· coming soon</em>}
            </li>
          ))}
        </ul>
      </main>
    </Layout>
  );
}
```

- [ ] **Step 2: Replace `site/src/pages/index.tsx`**

```tsx
import React from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

export default function Home(): JSX.Element {
  return (
    <Layout
      title="AP2 from First Principles"
      description="Learn the Agent Payments Protocol by building it, then mapping to the SDK.">
      <header className="hero hero--primary">
        <div className="container">
          <h1 className="hero__title">AP2 from First Principles</h1>
          <p className="hero__subtitle">
            Build the Agent Payments Protocol by hand — mandates, signing, roles,
            trust — then map every piece to the official SDK.
          </p>
          <div>
            <Link className="button button--secondary button--lg" to="/docs/why-agent-payments">
              Start with Lesson 00 →
            </Link>
          </div>
        </div>
      </header>
      <main className="container margin-vert--lg">
        <p>
          A public, incremental learning resource. Each lesson follows the same
          spine: <strong>Frame · Build · Map · Inspect · Check</strong>. Every
          code snippet here is real, tested code from the repo.
        </p>
        <p>
          New here? See the <Link to="/roadmap">roadmap</Link> or skim the{' '}
          <Link to="/glossary">glossary</Link>.
        </p>
      </main>
    </Layout>
  );
}
```

- [ ] **Step 3: Verify build**

Run: `cd site && npm run build 2>&1 | tail -20 && cd ..`
Expected: no errors on `roadmap.tsx` / `index.tsx` (lesson-doc link warnings acceptable until Task 14).

- [ ] **Step 4: Commit**

```bash
git add site/src/pages/roadmap.tsx site/src/pages/index.tsx
git commit -m "feat(site): roadmap and landing pages"
```

---

## Task 12: Lesson docs (MDX) + sidebar

Write the three lesson pages to the five-beat spine. Lesson 02 imports the real, tested code via `remark-code-import` (paths are relative to the MDX file; `../../lessons/...` and `../../ap2_shared/...` reach the repo root, allowed by the config from Task 9).

**Files:**
- Create: `site/docs/00-why-agent-payments.mdx`
- Create: `site/docs/01-roles-and-journeys.mdx`
- Create: `site/docs/02-mandates.mdx`
- Create: `site/sidebars.ts` (replace generated content)

- [ ] **Step 1: Create `site/sidebars.ts`**

```ts
import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  lessons: [
    'why-agent-payments',
    'roles-and-journeys',
    'mandates',
  ],
};

export default sidebars;
```

- [ ] **Step 2: Create `site/docs/00-why-agent-payments.mdx`**

Frontmatter + five beats. Required content (write in clear prose, ~400–700 words):

```mdx
---
slug: why-agent-payments
title: 00 · Why agent payments?
sidebar_position: 1
---

import Term from '@site/src/components/Term';
```

- **Frame:** Today's payment rails assume a human clicking a trusted UI. Agents break that assumption — raising four questions AP2 exists to answer: authorization/auditability, authenticity of intent, agent error/"hallucination", and accountability/liability. Introduce vocabulary with `<Term>`: <Term id="ap2">AP2</Term>, <Term id="verifiable-intent">Verifiable Intent</Term>. (Source: AP2 `docs/overview.md` §1.2–1.3, §2.3.)
- **Build:** show `trust_gap.py` via code-import and explain the contrast (no proof vs signed proof):
  ````
  ```py reference title="lessons/00-why-agent-payments/trust_gap.py"
  ../../lessons/00-why-agent-payments/trust_gap.py
  ```
  ````
- **Map:** connect "signed proof of intent" to AP2's principle "Verifiable Intent, Not Inferred Action" and forward-reference mandates (Lesson 02).
- **Inspect:** run `uv run python lessons/00-why-agent-payments/trust_gap.py`; show the `proof: None` vs a JWT string.
- **Check:** 3 recall prompts ("Name two of the four trust questions"; "Why isn't an LLM's say-so enough?"; "What replaces inferred action?") + link to `docs/overview.md`.

- [ ] **Step 3: Create `site/docs/01-roles-and-journeys.mdx`**

```mdx
---
slug: roles-and-journeys
title: 01 · The cast & the journeys
sidebar_position: 2
---

import Term from '@site/src/components/Term';
```

Required content (~500–800 words):
- **Frame:** introduce the six roles via `<Term>` (<Term id="shopping-agent">Shopping Agent</Term>, <Term id="credential-provider">Credential Provider</Term>, <Term id="merchant">Merchant</Term>, <Term id="merchant-payment-processor">Merchant Payment Processor</Term>, <Term id="trusted-surface">Trusted Surface</Term>, Network/Issuer) and the two journeys (<Term id="human-present">Human-Present</Term> vs <Term id="human-not-present">Human-Not-Present</Term>). (Source: `docs/overview.md` §3–4.)
- **Build:** code-import `roles.py`:
  ````
  ```py reference title="lessons/01-roles-and-journeys/roles.py"
  ../../lessons/01-roles-and-journeys/roles.py
  ```
  ````
- **Map:** note how roles can combine (SA can host its own CP; merchant can be its own MPP) — cite the "non-normative examples" in overview §3.
- **Inspect:** run `roles.py`; point out the Open→Closed mandate step in HNP (foreshadows Lesson 02/06).
- **Check:** 3 recall prompts ("Which role signs the cart?" → Merchant; "Where does the user actually consent?" → Trusted Surface; "What flips a mandate from Open to Closed?").

- [ ] **Step 4: Create `site/docs/02-mandates.mdx`**

```mdx
---
slug: mandates
title: 02 · Mandates, the unit of trust
sidebar_position: 3
---

import Term from '@site/src/components/Term';
```

Required content (~900–1300 words), the flagship lesson:
- **Frame:** a <Term id="mandate">Mandate</Term> = signed, hash-bound intent. Distinguish <Term id="checkout-mandate">Checkout Mandate</Term> vs <Term id="payment-mandate">Payment Mandate</Term>, and <Term id="open-mandate">Open</Term> vs <Term id="closed-mandate">Closed</Term>. Call out the terminology evolution (SDK still says `CartMandate`; spec says Checkout Mandate). (Sources: `docs/glossary.md`, `code/sdk/python/ap2/models/mandate.py`.)
- **Build:** explain a JWT from first principles, then code-import, in order:
  - the JOSE primitive:
    ````
    ```py reference title="ap2_shared/jose.py"
    ../../ap2_shared/jose.py
    ```
    ````
  - building the mandates:
    ````
    ```py reference title="lessons/02-mandates/build_mandate.py"
    ../../lessons/02-mandates/build_mandate.py
    ```
    ````
- **Inspect:** code-import `verify_mandate.py`, then show that tampering with the cart total flips verification to `False` (integrity via `cart_hash`), and an invalid signature also fails (authenticity):
  ````
  ```py reference title="lessons/02-mandates/verify_mandate.py"
  ../../lessons/02-mandates/verify_mandate.py
  ```
  ````
- **Map:** code-import `map_to_sdk.py`; explain that our dict is exactly `ap2.models.mandate.CartMandate` / `PaymentMandate`, and that the SDK's newer SD-JWT `CheckoutMandate` chain (`ap2.sdk`) is Lessons 03–04. Note that `PaymentMandate.user_authorization` is an SD-JWT VP in production (forward ref):
  ````
  ```py reference title="lessons/02-mandates/map_to_sdk.py"
  ../../lessons/02-mandates/map_to_sdk.py
  ```
  ````
- **Check:** 3 recall prompts ("Why two checks, signature *and* hash?"; "Who signs the Checkout Mandate vs the Payment Mandate?"; "What does Open→Closed mean?") + links to `models/mandate.py` and `sdk/README.md`.

- [ ] **Step 5: Verify the docs build (code-import must resolve real files)**

Run: `cd site && npm run build 2>&1 | tail -30 && cd ..`
Expected: build succeeds; if a `reference` path fails, fix the relative path (must resolve from the MDX file to repo-root `lessons/` and `ap2_shared/`).

- [ ] **Step 6: Commit**

```bash
git add site/docs site/sidebars.ts
git commit -m "docs(site): lessons 00-02 with imported, tested code snippets"
```

---

## Task 13: Blog post #1

**Files:**
- Create: `site/blog/2026-05-24-learning-ap2-from-first-principles.md`
- Create/Modify: `site/blog/authors.yml` (optional single author)

- [ ] **Step 1: Create the post**

```md
---
slug: learning-ap2-from-first-principles
title: Learning AP2 from first principles
authors: []
tags: [ap2, agentic-commerce]
date: 2026-05-24
---

I'm learning the Agent Payments Protocol the way that sticks: build each piece
by hand, then map it to the official SDK. This site is the public record.

<!-- truncate -->

The plan is simple and repeatable. Every lesson follows one spine —
**Frame · Build · Map · Inspect · Check** — so the concepts compound instead of
piling up. v1 covers the foundations: *why* agent payments need a protocol, the
*cast* of roles and the two journeys, and the heart of it all — *mandates*, the
unit of trust. From there: selective disclosure (SD-JWT), mandate chains and
receipts, the full Human-Present flow, autonomous Human-Not-Present delegation,
and how AP2 rides on A2A.

Start at [Lesson 00](/docs/why-agent-payments), or see the
[roadmap](/roadmap).
```

- [ ] **Step 2: Verify build**

Run: `cd site && npm run build 2>&1 | tail -20 && cd ..`
Expected: blog builds; the post appears at `/blog`.

- [ ] **Step 3: Commit**

```bash
git add site/blog
git commit -m "blog: kickoff post — learning AP2 from first principles"
```

---

## Task 14: Root README + full local verification

**Files:**
- Create: `README.md`
- Create: `vercel.json`

- [ ] **Step 1: Create `vercel.json`**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "installCommand": "cd site && npm install",
  "buildCommand": "cd site && npm run build",
  "outputDirectory": "site/build"
}
```

- [ ] **Step 2: Create `README.md`**

```markdown
# AP2 from First Principles

A public, incremental resource for learning the **Agent Payments Protocol (AP2)**
by building it by hand, then mapping each piece to the official `ap2` SDK.

**Live site:** _(added after first deploy — see Task 15)_

## Layout
- `lessons/NN-slug/` — runnable, tested lesson code.
- `ap2_shared/` — shared, installable JOSE primitives.
- `site/` — Docusaurus site (imports real snippets from the lessons).

## Prerequisites
- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)
- Node.js 18+

## Run the code
```bash
uv sync --extra dev
uv run pytest                         # all lesson tests
bash lessons/02-mandates/run.sh       # build → verify → map
```

## Run the site
```bash
cd site && npm install && npm run start
```

## Add a lesson
```bash
uv run python scripts/new-lesson.py 03 selective-disclosure
```

Design + plan live in `docs/superpowers/`.
```

- [ ] **Step 3: Full Python verification**

Run: `uv run pytest`
Expected: PASS — all tests across `ap2_shared`, `lessons`, and `scripts` green.

- [ ] **Step 4: Full site build verification**

Run: `cd site && npm run build && cd ..`
Expected: build succeeds with `onBrokenLinks: 'throw'` (no broken links now that all pages exist).

- [ ] **Step 5: Commit**

```bash
git add README.md vercel.json
git commit -m "docs: root README + vercel build config; v1 verified locally"
```

---

## Task 15: Deploy to Vercel + record the live URL

This task is interactive and its output (the URL) must be verified.

**Files:**
- Modify: `README.md` (add the live URL)
- Modify: `site/docusaurus.config.ts` (set `url` to the real deployment)

- [ ] **Step 1: Deploy**

Preferred: use the Vercel MCP `deploy_to_vercel` tool from the repo root (the runner should load its schema via ToolSearch first). Fallback: the Vercel CLI:

Run (fallback): `npx vercel --prod --yes`
Expected: a production URL like `https://ap2-getting-started-xxxx.vercel.app`.

- [ ] **Step 2: Verify the deployment is live**

Run: `curl -sS -o /dev/null -w "%{http_code}\n" <DEPLOYED_URL>`
Expected: `200`

- [ ] **Step 3: Record the URL**

Update `README.md` ("Live site:") and set `url` in `site/docusaurus.config.ts` to the deployed origin. Re-run `cd site && npm run build && cd ..` to confirm it still builds.

- [ ] **Step 4: Commit**

```bash
git add README.md site/docusaurus.config.ts
git commit -m "docs: record live Vercel URL for v1"
```

- [ ] **Step 5: Final confirmation (evidence before claiming done)**

Run: `uv run pytest -q && (cd site && npm run build >/dev/null && echo SITE_BUILD_OK)`
Expected: tests pass and `SITE_BUILD_OK`. With a `200` from Step 2, v1's definition of done is met.

---

## Self-Review

**Spec coverage:**
- Hybrid build-then-map → Tasks 3–5 (build) + 5/12 (map). ✅
- Docusaurus → Vercel → Tasks 9, 14, 15. ✅
- Monorepo, code-as-source via remark-code-import → Tasks 9, 12. ✅
- Five-beat spine → Task 12 enforces Frame/Build/Map/Inspect/Check per lesson. ✅
- Lessons 00–02 → Tasks 3–7, 12. ✅
- Lesson 02 runnable + pytest-passing → Tasks 3–6. ✅
- Glossary page + tooltips → Task 10. ✅
- Roadmap page → Task 11. ✅
- Blog post #1 → Task 13. ✅
- README + new-lesson scaffold → Tasks 8, 14. ✅
- DoD (pytest green, npm build green, Vercel URL live) → Tasks 14–15. ✅
- Git-pinned `ap2` (no PyPI) → Task 1 + committed `uv.lock`. ✅

**Placeholder scan:** No "TBD/implement later". MDX prose beats are specified as concrete required-content bullets with exact `<Term>` ids, code-import blocks, source citations, and recall prompts — not "write lesson here". The only intentionally deferred value is the live URL (produced by Task 15) and the `ap2` commit hash (pinned by `uv.lock`, not hardcodable in advance).

**Type/name consistency:** function names used in tests match implementations — `build_cart_contents`, `build_checkout_mandate(cart, priv, kid)`, `build_payment_mandate(checkout, priv, kid)`, `verify_checkout_mandate(mandate, pub)`, `to_sdk_cart_mandate(cart, jwt)`, `to_sdk_payment_mandate(...)`, and shared `make_jwt`/`verify_jwt`/`sha256_b64url`/`canonical_json`/`generate_p256_keypair`. Docusaurus doc slugs (`why-agent-payments`, `roles-and-journeys`, `mandates`) match `sidebars.ts`, navbar/footer links, and homepage CTA.
