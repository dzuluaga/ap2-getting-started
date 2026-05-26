# Lesson 03 — SD-JWT + key binding — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Lesson 03 ("Selective disclosure: SD-JWT & key binding") to the live AP2 learning site — a from-scratch issuer→holder→verifier flow with selective disclosure + KB-JWT, built on `ap2_shared`, then mapped to `ap2.sdk.sdjwt` and the AP2 `OpenPaymentMandate` pattern.

**Architecture:** Lean SD-JWT + KB-JWT primitives in a new `ap2_shared/sdjwt.py` (object-level selective disclosure only — no recursive/decoy/array-element disclosure). Lesson code in `lessons/03-selective-disclosure/` uses the primitives to tell a generic Build story and map to the SDK + an AP2 `OpenPaymentMandate` example in the Map. Docusaurus page `site/docs/03-selective-disclosure.mdx` follows the established five-beat spine and imports the real, tested code.

**Tech Stack:** Python 3.11+ with `uv`; `cryptography` + `ap2_shared.jose` (from Lesson 02) for the from-scratch build; the official `ap2` SDK (git-pinned) + `jwcrypto` for the Map; Docusaurus + TypeScript + `remark-code-import` for the site.

**Reference (read-only):** `/Users/diegozuluaga/tools/git/AP2/code/sdk/python/ap2/sdk/sdjwt/` (the SDK we map to) and `/Users/diegozuluaga/tools/git/AP2/code/sdk/python/ap2/sdk/README.md` (the canonical OpenPaymentMandate example). Spec: `docs/superpowers/specs/2026-05-25-lesson-03-sd-jwt-design.md`.

---

## File Structure

Created or modified by this plan:

```
ap2_shared/
├── jose.py                 # MODIFY: `make_jwt(...)` gains an optional `typ` kwarg (default "JWT")
├── test_jose.py            # MODIFY: append one test for the new typ param
├── sdjwt.py                # CREATE: make_disclosure / make_sdjwt / build_presentation /
│                           #          make_kb_jwt / attach_kb / verify
└── test_sdjwt.py           # CREATE: unit tests for the primitives
lessons/
└── 03-selective-disclosure/
    ├── README.md           # CREATE: short pointer + run instructions
    ├── build_sdjwt.py      # CREATE: issuer issues, holder presents (Build beat)
    ├── verify_sdjwt.py     # CREATE: verify + main() demoing 4 cases (Inspect beat)
    ├── map_to_sdk.py       # CREATE: SDK MandateClient flow with OpenPaymentMandate (Map beat)
    ├── test_sdjwt.py       # CREATE: lesson-level tests
    └── run.sh              # CREATE: build → verify → map
site/
├── src/data/glossary.ts    # MODIFY: add kb-jwt, cnf, issuer-holder-verifier, disclosure; refresh sd-jwt
├── src/pages/roadmap.tsx   # MODIFY: flip lesson 03 from coming-soon to ✅ available
├── sidebars.ts             # MODIFY: append 'selective-disclosure'
└── docs/
    └── 03-selective-disclosure.mdx   # CREATE: lesson page (five-beat spine, imports real code)
```

---

## Task 1: Extend `make_jwt` to accept a custom `typ`

KB-JWT requires `typ=kb+jwt` in the JWT header. We extend the existing `make_jwt` with an optional, backward-compatible `typ` kwarg so the KB primitive doesn't need to duplicate JOSE machinery.

**Files:**
- Modify: `ap2_shared/jose.py`
- Modify: `ap2_shared/test_jose.py`

- [ ] **Step 1: Append a failing test to `ap2_shared/test_jose.py`**

```python
def test_make_jwt_supports_custom_typ():
    import json
    priv, _ = generate_p256_keypair()
    token = make_jwt({"foo": "bar"}, priv, kid="m-1", typ="kb+jwt")
    head_b64 = token.split(".")[0]
    header = json.loads(b64url_decode(head_b64))
    assert header["typ"] == "kb+jwt"
    assert header["alg"] == "ES256"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest ap2_shared/test_jose.py::test_make_jwt_supports_custom_typ -q -W ignore::DeprecationWarning -o addopts=""`
Expected: FAIL (`make_jwt() got an unexpected keyword argument 'typ'`).

- [ ] **Step 3: Add the `typ` kwarg to `make_jwt` in `ap2_shared/jose.py`**

Replace the existing `make_jwt` body with:

```python
def make_jwt(payload: dict, private_key, kid: str, typ: str = "JWT") -> str:
    """Build a compact ES256 JWT from a payload dict.

    `typ` defaults to `"JWT"` (RFC 7519). Pass `"kb+jwt"` for a Key-Binding JWT.
    """
    header = {"alg": "ES256", "typ": typ, "kid": kid}
    encoded_header = b64url_encode(canonical_json(header))
    encoded_payload = b64url_encode(canonical_json(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = b64url_encode(_es256_sign(signing_input, private_key))
    return f"{encoded_header}.{encoded_payload}.{signature}"
```

- [ ] **Step 4: Run all of `test_jose.py` to verify everything still passes**

Run: `uv run pytest ap2_shared -q -W ignore::DeprecationWarning -o addopts=""`
Expected: PASS (existing tests + 1 new = 9 passed).

- [ ] **Step 5: Commit**

```bash
git add ap2_shared/jose.py ap2_shared/test_jose.py
git commit -m "feat(shared): make_jwt accepts custom typ (default JWT) for KB-JWT"
```

---

## Task 2: `ap2_shared/sdjwt.py` — `make_disclosure`

Foundational: one disclosure = `[salt, name, value]` JSON, base64url-encoded; its SHA-256 is what lands in `_sd`.

**Files:**
- Create: `ap2_shared/sdjwt.py`
- Create: `ap2_shared/test_sdjwt.py`

- [ ] **Step 1: Write failing tests in `ap2_shared/test_sdjwt.py`**

```python
import json

from ap2_shared.jose import b64url_decode, sha256_b64url
from ap2_shared.sdjwt import make_disclosure


def test_make_disclosure_round_trips_and_hashes_the_b64_string():
    disc, h = make_disclosure("country", "CA", salt="AAAAAAAAAAAAAAAAAAAAAA")
    salt, name, value = json.loads(b64url_decode(disc))
    assert salt == "AAAAAAAAAAAAAAAAAAAAAA"
    assert name == "country"
    assert value == "CA"
    # The hash is over the base64url-encoded disclosure bytes — what goes in _sd.
    assert h == sha256_b64url(disc.encode("ascii"))


def test_make_disclosure_generates_unique_salts_when_omitted():
    a, _ = make_disclosure("country", "CA")
    b, _ = make_disclosure("country", "CA")
    assert a != b  # Different salts → different disclosures even for same (name, value).
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest ap2_shared/test_sdjwt.py -q -W ignore::DeprecationWarning -o addopts=""`
Expected: FAIL with `ModuleNotFoundError: No module named 'ap2_shared.sdjwt'`.

- [ ] **Step 3: Create `ap2_shared/sdjwt.py`**

```python
"""From-scratch SD-JWT + KB-JWT primitives (lean: object-level selective
disclosure + key binding only). Built on top of `ap2_shared.jose` so the JOSE
mechanics from Lesson 02 are reused.

The point is pedagogical: SD-JWT is a JWT plus two ideas — (1) some claims are
moved into `[salt, name, value]` "disclosures" hashed into an `_sd` array, so
the holder picks which to reveal; (2) a key-binding JWT (KB-JWT, `typ=kb+jwt`)
signed by the holder's key (committed in `cnf` in the SD-JWT) covers the whole
presentation, so the verifier knows the holder really meant *these*
disclosures for *this* request (`aud`/`nonce`).

Wire format:

    <SD-JWT>~<disclosure_i>~...~[<KB-JWT>]~

The trailing `~` is always present; the KB-JWT is optional.
"""
from __future__ import annotations

import json
import secrets
import time
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ec

from ap2_shared.jose import (
    b64url_decode,
    b64url_encode,
    make_jwt,
    public_jwk,
    sha256_b64url,
    verify_jwt,
)


def make_disclosure(
    name: str, value: Any, salt: str | None = None
) -> tuple[str, str]:
    """Build one disclosure ``[salt, name, value]``.

    Returns ``(disclosure_b64url, hash_b64url)``. The hash is over the
    base64url-encoded disclosure bytes — what goes into ``_sd``.
    """
    if salt is None:
        salt = b64url_encode(secrets.token_bytes(16))
    blob = json.dumps([salt, name, value], separators=(",", ":")).encode("utf-8")
    disclosure_b64 = b64url_encode(blob)
    return disclosure_b64, sha256_b64url(disclosure_b64.encode("ascii"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest ap2_shared/test_sdjwt.py -q -W ignore::DeprecationWarning -o addopts=""`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add ap2_shared/sdjwt.py ap2_shared/test_sdjwt.py
git commit -m "feat(shared): SD-JWT primitive — make_disclosure"
```

---

## Task 3: `ap2_shared/sdjwt.py` — `make_sdjwt` + `build_presentation`

The issuer side (move sd-claims into disclosures + `_sd`; add `cnf`) and the holder's "build presentation" step (pick which disclosures to reveal).

**Files:**
- Modify: `ap2_shared/sdjwt.py`
- Modify: `ap2_shared/test_sdjwt.py`

- [ ] **Step 1: Append failing tests to `ap2_shared/test_sdjwt.py`**

```python
from ap2_shared.jose import decode_jwt_unverified, verify_jwt
from ap2_shared.keys import generate_p256_keypair
from ap2_shared.sdjwt import build_presentation, make_sdjwt


def _payload():
    return {"iss": "Bank", "sub": "alice", "country": "CA", "over_18": True}


def test_make_sdjwt_moves_sd_claims_to_disclosures_and_adds_sd_array():
    issuer_priv, issuer_pub = generate_p256_keypair()
    token, disclosures = make_sdjwt(
        payload=_payload(),
        sd_claims=["country", "over_18"],
        issuer_priv=issuer_priv,
        issuer_kid="bank-1",
    )
    # Signature is valid under the issuer's key.
    clear = verify_jwt(token, issuer_pub)
    assert clear is not None
    # The selectively-disclosed fields are gone from the clear payload.
    assert "country" not in clear and "over_18" not in clear
    # Their hashes ARE in _sd (one per sd_claim).
    assert isinstance(clear["_sd"], list) and len(clear["_sd"]) == 2
    # Disclosures dict returns one entry per sd_claim, keyed by name.
    assert set(disclosures.keys()) == {"country", "over_18"}


def test_make_sdjwt_includes_cnf_when_holder_pub_provided():
    issuer_priv, _ = generate_p256_keypair()
    _, holder_pub = generate_p256_keypair()
    token, _ = make_sdjwt(
        payload=_payload(),
        sd_claims=["country"],
        issuer_priv=issuer_priv,
        issuer_kid="bank-1",
        holder_pub=holder_pub,
    )
    clear = decode_jwt_unverified(token)
    assert clear["cnf"]["jwk"]["kty"] == "EC"
    assert clear["cnf"]["jwk"]["crv"] == "P-256"


def test_make_sdjwt_raises_when_sd_claim_missing():
    import pytest
    issuer_priv, _ = generate_p256_keypair()
    with pytest.raises(KeyError):
        make_sdjwt(
            payload={"iss": "Bank"},
            sd_claims=["country"],
            issuer_priv=issuer_priv,
            issuer_kid="bank-1",
        )


def test_build_presentation_includes_only_revealed_disclosures():
    issuer_priv, _ = generate_p256_keypair()
    token, disclosures = make_sdjwt(
        payload=_payload(),
        sd_claims=["country", "over_18"],
        issuer_priv=issuer_priv,
        issuer_kid="bank-1",
    )
    pres = build_presentation(
        sdjwt_token=token, disclosures=disclosures, reveal=["country"]
    )
    # Wire format: <sdjwt>~<disclosure>~  (always ends with ~)
    assert pres.endswith("~")
    parts = pres.rstrip("~").split("~")
    assert parts[0] == token
    assert parts[1] == disclosures["country"]
    assert disclosures["over_18"] not in pres
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest ap2_shared/test_sdjwt.py -q -W ignore::DeprecationWarning -o addopts=""`
Expected: FAIL with `ImportError: cannot import name 'make_sdjwt'` (or similar).

- [ ] **Step 3: Append to `ap2_shared/sdjwt.py`**

```python
def make_sdjwt(
    *,
    payload: dict,
    sd_claims: list[str],
    issuer_priv,
    issuer_kid: str,
    holder_pub=None,
) -> tuple[str, dict[str, str]]:
    """Issue an SD-JWT.

    For each name in ``sd_claims``: move the value out of the clear payload
    into a disclosure (`make_disclosure`), and put its hash in ``_sd``. If
    ``holder_pub`` is provided, add ``cnf: {jwk: ...}`` so the verifier can
    identify the holder for KB. Returns the signed SD-JWT plus the disclosures
    keyed by claim name.
    """
    clear = dict(payload)
    disclosures: dict[str, str] = {}
    sd_hashes: list[str] = []
    for name in sd_claims:
        if name not in clear:
            raise KeyError(f"sd_claim {name!r} not in payload")
        value = clear.pop(name)
        disc, h = make_disclosure(name, value)
        disclosures[name] = disc
        sd_hashes.append(h)
    clear["_sd"] = sd_hashes
    if holder_pub is not None:
        clear["cnf"] = {"jwk": public_jwk(holder_pub)}
    return make_jwt(clear, issuer_priv, kid=issuer_kid), disclosures


def build_presentation(
    *, sdjwt_token: str, disclosures: dict[str, str], reveal: list[str]
) -> str:
    """Holder's presentation up to (but not including) any KB-JWT.

    Returns ``<sdjwt>~<disc_i>~...~`` — only disclosures for claim names in
    ``reveal``, in the caller's order. Always ends with ``~``.
    """
    parts = [sdjwt_token]
    for name in reveal:
        if name not in disclosures:
            raise KeyError(f"no disclosure for {name!r}")
        parts.append(disclosures[name])
    return "~".join(parts) + "~"
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest ap2_shared/test_sdjwt.py -q -W ignore::DeprecationWarning -o addopts=""`
Expected: PASS (6 passed total in this file).

- [ ] **Step 5: Commit**

```bash
git add ap2_shared/sdjwt.py ap2_shared/test_sdjwt.py
git commit -m "feat(shared): SD-JWT — make_sdjwt + build_presentation"
```

---

## Task 4: `ap2_shared/sdjwt.py` — `make_kb_jwt` + `attach_kb`

The holder's key-binding step. The KB-JWT's `sd_hash` covers the entire presentation up to the KB (so swapping disclosures breaks the binding). `now` is injectable for deterministic tests.

**Files:**
- Modify: `ap2_shared/sdjwt.py`
- Modify: `ap2_shared/test_sdjwt.py`

- [ ] **Step 1: Append failing tests**

```python
from ap2_shared.jose import decode_jwt_unverified
from ap2_shared.sdjwt import attach_kb, make_kb_jwt


def test_make_kb_jwt_signs_with_typ_kb_jwt_and_correct_sd_hash():
    holder_priv, holder_pub = generate_p256_keypair()
    presentation_no_kb = "ey....jwt~ZGlzYzE~"  # arbitrary; we hash whatever we pass
    kb = make_kb_jwt(
        presentation_no_kb=presentation_no_kb,
        aud="merchant.example",
        nonce="txn-001",
        holder_priv=holder_priv,
        holder_kid="alice-1",
        now=1700000000,
    )
    head = json.loads(b64url_decode(kb.split(".")[0]))
    payload = decode_jwt_unverified(kb)
    assert head["typ"] == "kb+jwt"
    assert head["alg"] == "ES256"
    assert payload["aud"] == "merchant.example"
    assert payload["nonce"] == "txn-001"
    assert payload["iat"] == 1700000000
    assert payload["sd_hash"] == sha256_b64url(presentation_no_kb.encode("ascii"))
    # And the signature verifies under the holder's public key.
    assert verify_jwt(kb, holder_pub) is not None


def test_attach_kb_concatenates_and_keeps_trailing_tilde():
    out = attach_kb("ey....jwt~ZGlzYzE~", "ey....kb")
    assert out == "ey....jwt~ZGlzYzE~ey....kb~"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest ap2_shared/test_sdjwt.py -q -W ignore::DeprecationWarning -o addopts=""`
Expected: FAIL with `ImportError: cannot import name 'make_kb_jwt'`.

- [ ] **Step 3: Append to `ap2_shared/sdjwt.py`**

```python
def make_kb_jwt(
    *,
    presentation_no_kb: str,
    aud: str,
    nonce: str,
    holder_priv,
    holder_kid: str,
    now: int | None = None,
) -> str:
    """Sign a Key-Binding JWT that covers ``presentation_no_kb``.

    ``sd_hash`` is SHA-256 over the *entire* presentation-up-to-KB (including
    its trailing ``~``), so any change to which disclosures the holder
    includes invalidates the KB.
    """
    sd_hash = sha256_b64url(presentation_no_kb.encode("ascii"))
    payload = {
        "aud": aud,
        "nonce": nonce,
        "iat": int(time.time()) if now is None else now,
        "sd_hash": sd_hash,
    }
    return make_jwt(payload, holder_priv, kid=holder_kid, typ="kb+jwt")


def attach_kb(presentation_no_kb: str, kb_jwt: str) -> str:
    """Append a KB-JWT to a presentation, with the trailing ``~``."""
    return presentation_no_kb + kb_jwt + "~"
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest ap2_shared/test_sdjwt.py -q -W ignore::DeprecationWarning -o addopts=""`
Expected: PASS (8 passed total).

- [ ] **Step 5: Commit**

```bash
git add ap2_shared/sdjwt.py ap2_shared/test_sdjwt.py
git commit -m "feat(shared): SD-JWT — make_kb_jwt + attach_kb"
```

---

## Task 5: `ap2_shared/sdjwt.py` — `verify`

The unified verifier: issuer signature + (if KB present) KB signature + `sd_hash` + optional `aud`/`nonce`; rebuilds revealed claims from `_sd` matching.

**Files:**
- Modify: `ap2_shared/sdjwt.py`
- Modify: `ap2_shared/test_sdjwt.py`

- [ ] **Step 1: Append failing tests**

```python
from ap2_shared.sdjwt import verify


def _issue_and_present(reveal, *, aud="merchant.example", nonce="txn-001",
                      attacker_kb=False, tamper_country=False):
    """Test helper: issue a credential, present with KB, optionally tamper."""
    issuer_priv, issuer_pub = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    token, disclosures = make_sdjwt(
        payload={"iss": "Bank", "sub": "alice", "country": "CA", "over_18": True},
        sd_claims=["country", "over_18"],
        issuer_priv=issuer_priv, issuer_kid="bank-1",
        holder_pub=holder_pub,
    )
    if tamper_country:
        # Swap country disclosure for one with a different value.
        evil, _ = make_disclosure("country", "ZZ")
        disclosures = dict(disclosures, country=evil)
    pres_no_kb = build_presentation(
        sdjwt_token=token, disclosures=disclosures, reveal=reveal
    )
    if attacker_kb:
        bad_priv, _ = generate_p256_keypair()
        kb = make_kb_jwt(
            presentation_no_kb=pres_no_kb, aud=aud, nonce=nonce,
            holder_priv=bad_priv, holder_kid="bad-1", now=1700000000,
        )
    else:
        kb = make_kb_jwt(
            presentation_no_kb=pres_no_kb, aud=aud, nonce=nonce,
            holder_priv=holder_priv, holder_kid="alice-1", now=1700000000,
        )
    return attach_kb(pres_no_kb, kb), issuer_pub, pres_no_kb


def test_verify_returns_only_revealed_claims():
    pres, issuer_pub, _ = _issue_and_present(reveal=["country", "over_18"])
    out = verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="merchant.example", expected_nonce="txn-001",
    )
    assert out is not None
    assert out["country"] == "CA"
    assert out["over_18"] is True
    assert out["iss"] == "Bank" and out["sub"] == "alice"
    assert "_sd" not in out and "cnf" not in out


def test_verify_rejects_tampered_disclosure():
    pres, issuer_pub, _ = _issue_and_present(reveal=["country"], tamper_country=True)
    assert verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="merchant.example", expected_nonce="txn-001",
    ) is None


def test_verify_rejects_wrong_holder_key_on_kb():
    pres, issuer_pub, _ = _issue_and_present(reveal=["country"], attacker_kb=True)
    assert verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="merchant.example", expected_nonce="txn-001",
    ) is None


def test_verify_rejects_missing_kb_when_aud_required():
    # Build a presentation with no KB.
    issuer_priv, issuer_pub = generate_p256_keypair()
    _, holder_pub = generate_p256_keypair()
    token, disclosures = make_sdjwt(
        payload={"iss": "Bank", "sub": "alice", "country": "CA"},
        sd_claims=["country"],
        issuer_priv=issuer_priv, issuer_kid="bank-1",
        holder_pub=holder_pub,
    )
    pres = build_presentation(
        sdjwt_token=token, disclosures=disclosures, reveal=["country"]
    )
    assert verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="merchant.example",
    ) is None


def test_verify_rejects_mismatched_aud():
    pres, issuer_pub, _ = _issue_and_present(reveal=["country"])
    assert verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="wrong.example", expected_nonce="txn-001",
    ) is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest ap2_shared/test_sdjwt.py -q -W ignore::DeprecationWarning -o addopts=""`
Expected: FAIL with `ImportError: cannot import name 'verify'`.

- [ ] **Step 3: Append to `ap2_shared/sdjwt.py`**

```python
def verify(
    *,
    presentation: str,
    issuer_pub,
    expected_aud: str | None = None,
    expected_nonce: str | None = None,
) -> dict | None:
    """Verify an SD-JWT presentation (issuer sig + KB binding + selective
    disclosure). Returns the merged-and-revealed claims, or ``None`` on any
    failure. KB-JWT is always verified if present; ``aud``/``nonce`` are only
    checked when ``expected_*`` is provided.
    """
    parts = presentation.split("~")
    # Wire format always ends with "~" → parts has a trailing "".
    if not parts or parts[-1] != "":
        return None
    parts = parts[:-1]
    if not parts:
        return None
    sdjwt_token, *rest = parts
    # KB present iff the LAST segment is a JWT (3 dot-separated parts).
    kb_jwt: str | None = None
    if rest and rest[-1].count(".") == 2:
        kb_jwt = rest[-1]
        disclosure_strs = rest[:-1]
    else:
        disclosure_strs = rest

    # 1) Issuer signature.
    clear = verify_jwt(sdjwt_token, issuer_pub)
    if clear is None:
        return None
    sd_array = clear.get("_sd", [])
    if not isinstance(sd_array, list):
        return None

    # 2) KB-JWT (if present, ALWAYS verify; otherwise enforce expected_*).
    if kb_jwt is not None:
        cnf = (clear.get("cnf") or {}).get("jwk")
        if not isinstance(cnf, dict):
            return None
        try:
            x = int.from_bytes(b64url_decode(cnf["x"]), "big")
            y = int.from_bytes(b64url_decode(cnf["y"]), "big")
            holder_pub = ec.EllipticCurvePublicNumbers(
                x, y, ec.SECP256R1()
            ).public_key()
        except (KeyError, ValueError):
            return None
        kb_payload = verify_jwt(kb_jwt, holder_pub)
        if kb_payload is None:
            return None
        presentation_no_kb = (
            sdjwt_token + "".join("~" + d for d in disclosure_strs) + "~"
        )
        if kb_payload.get("sd_hash") != sha256_b64url(
            presentation_no_kb.encode("ascii")
        ):
            return None
        if expected_aud is not None and kb_payload.get("aud") != expected_aud:
            return None
        if expected_nonce is not None and kb_payload.get("nonce") != expected_nonce:
            return None
    elif expected_aud is not None or expected_nonce is not None:
        return None  # KB required by caller but missing.

    # 3) Reconstruct revealed claims by matching disclosure hashes to _sd.
    revealed: dict[str, Any] = {}
    for disc in disclosure_strs:
        h = sha256_b64url(disc.encode("ascii"))
        if h not in sd_array:
            return None
        try:
            _salt, name, value = json.loads(b64url_decode(disc))
        except (ValueError, TypeError):
            return None
        revealed[name] = value

    # 4) Merge: non-_sd / non-cnf clear claims + revealed disclosures.
    out = {k: v for k, v in clear.items() if k not in ("_sd", "cnf")}
    out.update(revealed)
    return out
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest ap2_shared/test_sdjwt.py -q -W ignore::DeprecationWarning -o addopts=""`
Expected: PASS (13 passed total).

- [ ] **Step 5: Commit**

```bash
git add ap2_shared/sdjwt.py ap2_shared/test_sdjwt.py
git commit -m "feat(shared): SD-JWT — verify (issuer sig + KB binding + selective disclosure)"
```

---

## Task 6: Lesson 03 — `build_sdjwt.py`

The generic Build scenario: Bank issues a credential to Alice; Alice presents to a merchant revealing only `country` + `over_18`, bound by KB-JWT.

**Files:**
- Create: `lessons/03-selective-disclosure/build_sdjwt.py`
- Create: `lessons/03-selective-disclosure/test_sdjwt.py` (extended in later tasks)

- [ ] **Step 1: Write failing tests in `lessons/03-selective-disclosure/test_sdjwt.py`**

```python
from ap2_shared.keys import generate_p256_keypair
from ap2_shared.sdjwt import verify

import build_sdjwt


def test_credential_round_trip_reveals_only_subset():
    issuer_priv, issuer_pub = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    assert set(disclosures.keys()) == set(build_sdjwt.SD_CLAIMS)

    pres = build_sdjwt.hold_and_present(
        sdjwt, disclosures,
        reveal=["country", "over_18"],
        holder_priv=holder_priv, holder_kid="alice-1",
        aud="merchant.example", nonce="txn-001", now=1700000000,
    )
    out = verify(
        presentation=pres, issuer_pub=issuer_pub,
        expected_aud="merchant.example", expected_nonce="txn-001",
    )
    assert out is not None
    assert out["country"] == "CA"
    assert out["over_18"] is True
    # The unrevealed claims must NOT leak.
    for hidden in ("name", "account_id", "account_tier"):
        assert hidden not in out
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest lessons/03-selective-disclosure/test_sdjwt.py -q -W ignore::DeprecationWarning -o addopts=""`
Expected: FAIL with `ModuleNotFoundError: No module named 'build_sdjwt'`.

- [ ] **Step 3: Create `lessons/03-selective-disclosure/build_sdjwt.py`**

```python
"""Lesson 03 — Issue an SD-JWT credential and present it selectively.

The story: "Bank of Examples" issues Alice a credential with five claims, all
selectively disclosable. Alice (the holder) presents to a merchant revealing
only `country` and `over_18`, with a KB-JWT binding the presentation to the
merchant for this specific transaction.

SD-JWT vocab to keep in your head while reading:
- Disclosure: `base64url(json([salt, name, value]))`. The holder may show it.
- `_sd`: array of disclosure hashes inside the issuer-signed SD-JWT — locks
  which claims exist (even when their values are not yet revealed).
- `cnf`: confirmation key — the holder's public JWK, carried in the SD-JWT.
- KB-JWT: signed by the holder for a given `(aud, nonce, sd_hash)`.
"""
from __future__ import annotations

from ap2_shared.keys import generate_p256_keypair
from ap2_shared.sdjwt import (
    attach_kb,
    build_presentation,
    make_kb_jwt,
    make_sdjwt,
)


SD_CLAIMS = ["name", "country", "account_id", "over_18", "account_tier"]


def issue_credential(issuer_priv, issuer_kid, holder_pub):
    """Bank of Examples issues Alice's credential."""
    payload = {
        "iss": "Bank of Examples",
        "sub": "user_alice",
        "name": "Alice Example",
        "country": "CA",
        "account_id": "AE-9001",
        "over_18": True,
        "account_tier": "gold",
    }
    return make_sdjwt(
        payload=payload,
        sd_claims=SD_CLAIMS,
        issuer_priv=issuer_priv,
        issuer_kid=issuer_kid,
        holder_pub=holder_pub,
    )


def hold_and_present(
    sdjwt_token,
    disclosures,
    *,
    reveal,
    holder_priv,
    holder_kid,
    aud,
    nonce,
    now=None,
):
    """Holder picks which claims to reveal + signs a KB binding the
    presentation to (aud, nonce)."""
    presentation_no_kb = build_presentation(
        sdjwt_token=sdjwt_token,
        disclosures=disclosures,
        reveal=reveal,
    )
    kb = make_kb_jwt(
        presentation_no_kb=presentation_no_kb,
        aud=aud,
        nonce=nonce,
        holder_priv=holder_priv,
        holder_kid=holder_kid,
        now=now,
    )
    return attach_kb(presentation_no_kb, kb)


def main() -> None:
    issuer_priv, _ = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = issue_credential(issuer_priv, "bank-1", holder_pub)
    print("SD-JWT issued by 'Bank of Examples'.")
    print("Selectively-disclosable claims:", list(disclosures.keys()))

    pres = hold_and_present(
        sdjwt, disclosures,
        reveal=["country", "over_18"],
        holder_priv=holder_priv,
        holder_kid="alice-1",
        aud="merchant.example",
        nonce="txn-001",
    )
    print("\nHolder presents to merchant (revealing country, over_18 only):")
    print(pres)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest lessons/03-selective-disclosure -q -W ignore::DeprecationWarning -o addopts=""`
Expected: PASS (1 passed).

- [ ] **Step 5: Run the demo**

Run: `uv run python lessons/03-selective-disclosure/build_sdjwt.py`
Expected: Prints "SD-JWT issued…", the 5 claim names, and a long `eyJ…~…~…~eyJ…~`-formatted presentation.

- [ ] **Step 6: Commit**

```bash
git add lessons/03-selective-disclosure/build_sdjwt.py lessons/03-selective-disclosure/test_sdjwt.py
git commit -m "feat(lesson-03): issue + selectively present an SD-JWT credential"
```

---

## Task 7: Lesson 03 — `verify_sdjwt.py` + four-failure-mode demo

Wraps `ap2_shared.sdjwt.verify` for the lesson's scenario and produces the four-case demo (valid / tampered / wrong-key-KB / missing-KB).

**Files:**
- Create: `lessons/03-selective-disclosure/verify_sdjwt.py`
- Modify: `lessons/03-selective-disclosure/test_sdjwt.py` (append tests)

- [ ] **Step 1: Append failing tests**

```python
import verify_sdjwt
from ap2_shared.sdjwt import (
    attach_kb,
    build_presentation,
    make_disclosure,
    make_kb_jwt,
)


def test_lesson_valid_presentation_verifies():
    issuer_priv, issuer_pub = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    pres = build_sdjwt.hold_and_present(
        sdjwt, disclosures,
        reveal=["country", "over_18"],
        holder_priv=holder_priv, holder_kid="alice-1",
        aud="merchant.example", nonce="txn-001", now=1700000000,
    )
    out = verify_sdjwt.verify_presentation(
        pres, issuer_pub, aud="merchant.example", nonce="txn-001"
    )
    assert out is not None and out["country"] == "CA"


def test_lesson_tampered_disclosure_fails():
    issuer_priv, issuer_pub = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    evil, _ = make_disclosure("over_18", False)
    evil_disclosures = dict(disclosures, over_18=evil)
    pres_no_kb = build_presentation(
        sdjwt_token=sdjwt, disclosures=evil_disclosures,
        reveal=["country", "over_18"],
    )
    kb = make_kb_jwt(
        presentation_no_kb=pres_no_kb,
        aud="merchant.example", nonce="txn-001",
        holder_priv=holder_priv, holder_kid="alice-1", now=1700000000,
    )
    pres = attach_kb(pres_no_kb, kb)
    assert verify_sdjwt.verify_presentation(
        pres, issuer_pub, aud="merchant.example", nonce="txn-001"
    ) is None


def test_lesson_wrong_holder_key_on_kb_fails():
    issuer_priv, issuer_pub = generate_p256_keypair()
    _, holder_pub = generate_p256_keypair()
    attacker_priv, _ = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    pres_no_kb = build_presentation(
        sdjwt_token=sdjwt, disclosures=disclosures,
        reveal=["country"],
    )
    kb = make_kb_jwt(
        presentation_no_kb=pres_no_kb,
        aud="merchant.example", nonce="txn-001",
        holder_priv=attacker_priv, holder_kid="attacker", now=1700000000,
    )
    pres = attach_kb(pres_no_kb, kb)
    assert verify_sdjwt.verify_presentation(
        pres, issuer_pub, aud="merchant.example", nonce="txn-001"
    ) is None


def test_lesson_missing_kb_when_aud_required_fails():
    issuer_priv, issuer_pub = generate_p256_keypair()
    _, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    pres = build_presentation(
        sdjwt_token=sdjwt, disclosures=disclosures, reveal=["country"]
    )  # no KB attached
    assert verify_sdjwt.verify_presentation(
        pres, issuer_pub, aud="merchant.example", nonce="txn-001"
    ) is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest lessons/03-selective-disclosure -q -W ignore::DeprecationWarning -o addopts=""`
Expected: FAIL with `ModuleNotFoundError: No module named 'verify_sdjwt'`.

- [ ] **Step 3: Create `lessons/03-selective-disclosure/verify_sdjwt.py`**

```python
"""Lesson 03 — Verify an SD-JWT presentation, with four failure-mode demos.

A presentation is trustworthy only when *three* checks pass:
1. **Authenticity** — the SD-JWT signature is valid under the issuer's key.
2. **Holder binding** — the KB-JWT is signed by the key in the SD-JWT's
   ``cnf``, and its ``sd_hash`` covers the exact presentation it accompanies
   (swap disclosures → broken).
3. **Selective disclosure integrity** — every presented disclosure hashes to
   a value already in the issuer-signed ``_sd`` array. The holder cannot
   forge new claims or change values.
"""
from __future__ import annotations

from ap2_shared.keys import generate_p256_keypair
from ap2_shared.sdjwt import (
    attach_kb,
    build_presentation,
    make_disclosure,
    make_kb_jwt,
    verify,
)

import build_sdjwt


def verify_presentation(presentation, issuer_pub, *, aud, nonce):
    """Verify a presentation, requiring KB with matching (aud, nonce)."""
    return verify(
        presentation=presentation,
        issuer_pub=issuer_pub,
        expected_aud=aud,
        expected_nonce=nonce,
    )


def main() -> None:
    issuer_priv, issuer_pub = generate_p256_keypair()
    holder_priv, holder_pub = generate_p256_keypair()
    sdjwt, disclosures = build_sdjwt.issue_credential(
        issuer_priv, "bank-1", holder_pub
    )
    aud, nonce = "merchant.example", "txn-001"

    # 1) Valid presentation.
    pres = build_sdjwt.hold_and_present(
        sdjwt, disclosures,
        reveal=["country", "over_18"],
        holder_priv=holder_priv, holder_kid="alice-1",
        aud=aud, nonce=nonce,
    )
    print(
        "Valid presentation verifies:",
        verify_presentation(pres, issuer_pub, aud=aud, nonce=nonce) is not None,
    )

    # 2) Tampered disclosure (swap over_18=True for over_18=False).
    evil, _ = make_disclosure("over_18", False)
    evil_disclosures = dict(disclosures, over_18=evil)
    evil_pres_no_kb = build_presentation(
        sdjwt_token=sdjwt, disclosures=evil_disclosures,
        reveal=["country", "over_18"],
    )
    evil_kb = make_kb_jwt(
        presentation_no_kb=evil_pres_no_kb, aud=aud, nonce=nonce,
        holder_priv=holder_priv, holder_kid="alice-1",
    )
    print(
        "Tampered disclosure verifies:",
        verify_presentation(attach_kb(evil_pres_no_kb, evil_kb),
                            issuer_pub, aud=aud, nonce=nonce),
        "(expected None)",
    )

    # 3) Wrong holder key on KB (attacker key, not the cnf key).
    attacker_priv, _ = generate_p256_keypair()
    bad_pres_no_kb = build_presentation(
        sdjwt_token=sdjwt, disclosures=disclosures, reveal=["country"]
    )
    bad_kb = make_kb_jwt(
        presentation_no_kb=bad_pres_no_kb, aud=aud, nonce=nonce,
        holder_priv=attacker_priv, holder_kid="attacker",
    )
    print(
        "Wrong-key KB verifies:",
        verify_presentation(attach_kb(bad_pres_no_kb, bad_kb),
                            issuer_pub, aud=aud, nonce=nonce),
        "(expected None)",
    )

    # 4) Missing KB when aud/nonce are required.
    no_kb = build_presentation(
        sdjwt_token=sdjwt, disclosures=disclosures, reveal=["country"]
    )
    print(
        "Missing KB verifies:",
        verify_presentation(no_kb, issuer_pub, aud=aud, nonce=nonce),
        "(expected None)",
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify tests pass**

Run: `uv run pytest lessons/03-selective-disclosure -q -W ignore::DeprecationWarning -o addopts=""`
Expected: PASS (5 passed total in lesson dir).

- [ ] **Step 5: Run the demo**

Run: `uv run python lessons/03-selective-disclosure/verify_sdjwt.py`
Expected output:
```
Valid presentation verifies: True
Tampered disclosure verifies: None (expected None)
Wrong-key KB verifies: None (expected None)
Missing KB verifies: None (expected None)
```

- [ ] **Step 6: Commit**

```bash
git add lessons/03-selective-disclosure/verify_sdjwt.py lessons/03-selective-disclosure/test_sdjwt.py
git commit -m "feat(lesson-03): verify_sdjwt + 4-failure-mode demo"
```

---

## Task 8: Lesson 03 — `map_to_sdk.py` (SDK + AP2 OpenPaymentMandate)

Maps the hand-built flow onto the SDK's `MandateClient`, then runs the AP2-native scenario (`OpenPaymentMandate` with constraints + `cnf` → agent presents → merchant verifies). This is the Map beat.

**Files:**
- Create: `lessons/03-selective-disclosure/map_to_sdk.py`
- Modify: `lessons/03-selective-disclosure/test_sdjwt.py` (append test)

- [ ] **Step 1: Append a failing test**

```python
def test_sdk_open_payment_mandate_flow_verifies():
    import map_to_sdk
    payloads = map_to_sdk.open_payment_mandate_flow()
    # The SDK returns a list of per-token effective payloads for chains.
    assert isinstance(payloads, list) and len(payloads) >= 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest lessons/03-selective-disclosure -q -W ignore::DeprecationWarning -o addopts=""`
Expected: FAIL with `ModuleNotFoundError: No module named 'map_to_sdk'`.

- [ ] **Step 3: Create `lessons/03-selective-disclosure/map_to_sdk.py`**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest lessons/03-selective-disclosure -q -W ignore::DeprecationWarning -o addopts=""`
Expected: PASS (6 passed total).

- [ ] **Step 5: Run the demo**

Run: `uv run python lessons/03-selective-disclosure/map_to_sdk.py`
Expected: `AP2 SDK verified the OpenPaymentMandate → PaymentMandate flow.` and a non-zero payload count.

- [ ] **Step 6: Commit**

```bash
git add lessons/03-selective-disclosure/map_to_sdk.py lessons/03-selective-disclosure/test_sdjwt.py
git commit -m "feat(lesson-03): map to ap2.sdk.sdjwt + OpenPaymentMandate example"
```

---

## Task 9: Lesson 03 — `run.sh` + `README.md`

**Files:**
- Create: `lessons/03-selective-disclosure/run.sh`
- Create: `lessons/03-selective-disclosure/README.md`

- [ ] **Step 1: Create `lessons/03-selective-disclosure/run.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo root
echo "== build ==";  uv run python lessons/03-selective-disclosure/build_sdjwt.py
echo; echo "== verify =="; uv run python lessons/03-selective-disclosure/verify_sdjwt.py
echo; echo "== map ==";    uv run python lessons/03-selective-disclosure/map_to_sdk.py
```

- [ ] **Step 2: Create `lessons/03-selective-disclosure/README.md`**

```markdown
# Lesson 03 — Selective disclosure (SD-JWT & key binding)

Open the SD-JWT black box from Lesson 02. Build an **issuer → holder → verifier**
flow with selective disclosure + key binding by hand, then map to
`ap2.sdk.sdjwt` and the AP2 `OpenPaymentMandate` pattern.

## Run

```bash
bash run.sh                                          # build → verify → map
uv run pytest lessons/03-selective-disclosure -q     # tests
```

## Files
- `build_sdjwt.py` — issuer issues a credential; holder presents selectively + KB.
- `verify_sdjwt.py` — verify a presentation; main() demos the four failure modes.
- `map_to_sdk.py` — the same flow via `ap2.sdk.sdjwt` + an AP2 `OpenPaymentMandate` example.

The full narrative lives on the site: **/docs/selective-disclosure**.
```

- [ ] **Step 3: Make `run.sh` executable and run it**

Run: `chmod +x lessons/03-selective-disclosure/run.sh && bash lessons/03-selective-disclosure/run.sh`
Expected: all three sections print without errors; the `verify` section prints `True / None / None / None`.

- [ ] **Step 4: Commit**

```bash
git add lessons/03-selective-disclosure/run.sh lessons/03-selective-disclosure/README.md
git commit -m "docs(lesson-03): run.sh + lesson README"
```

---

## Task 10: Site — glossary additions + refresh

**Files:**
- Modify: `site/src/data/glossary.ts`

- [ ] **Step 1: Refresh the `sd-jwt` entry and add four new entries**

In `site/src/data/glossary.ts`, replace the existing `sd-jwt` entry:

```ts
  {id: 'sd-jwt', term: 'SD-JWT',
   short: 'A JWT whose claims can be revealed individually via base64url-encoded [salt, name, value] disclosures hashed into an `_sd` array.',
   spec: 'Selective Disclosure JWT (RFC 9901); foundation of AP2 mandates with key binding.'},
```

…and add these four entries immediately after the `sd-jwt` entry (the order keeps related terms together):

```ts
  {id: 'disclosure', term: 'Disclosure',
   short: '`[salt, name, value]` triple revealed by the holder; base64url-encoded and hashed into `_sd`.',
   spec: 'The unit of selective disclosure in SD-JWT; the verifier hashes a presented disclosure and looks it up in `_sd`.'},
  {id: 'cnf', term: 'cnf (Holder Key)',
   short: 'Confirmation claim in the SD-JWT carrying the holder\'s public JWK — the key that signs KB-JWT.',
   spec: 'Confirmation method (RFC 7800) that binds a token to a holder key, so a verifier knows who is allowed to present it.'},
  {id: 'kb-jwt', term: 'KB-JWT (Key-Binding JWT)',
   short: 'A JWT signed by the holder over `(aud, nonce, iat, sd_hash)` proving they intend *this* presentation for *this* verifier.',
   spec: 'Key-Binding JWT (RFC 9901, `typ=kb+jwt`); `sd_hash` covers the entire presentation up to the KB.'},
  {id: 'issuer-holder-verifier', term: 'Issuer–Holder–Verifier',
   short: 'The three-party trust model SD-JWT formalizes: issuer signs, holder presents selectively, verifier checks.',
   spec: 'Roles defined by the W3C/IETF verifiable-credentials model; AP2 maps them to Bank → Shopping Agent → Merchant.'},
```

- [ ] **Step 2: Verify the site still typechecks**

Run: `cd site && npm run typecheck`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add site/src/data/glossary.ts
git commit -m "docs(site): glossary additions for SD-JWT, disclosure, cnf, KB-JWT, issuer-holder-verifier"
```

---

## Task 11: Site — roadmap + sidebar

**Files:**
- Modify: `site/src/pages/roadmap.tsx`
- Modify: `site/sidebars.ts`

- [ ] **Step 1: Flip Lesson 03 from "coming soon" to "available" in `site/src/pages/roadmap.tsx`**

Find the line `{n: '03', title: 'Selective disclosure: SD-JWT & key binding', v1: false},` and change `v1: false` to `v1: true`.

- [ ] **Step 2: Append `'selective-disclosure'` to the sidebar in `site/sidebars.ts`**

Replace the `lessons` array with:

```ts
  lessons: [
    'why-agent-payments',
    'roles-and-journeys',
    'mandates',
    'selective-disclosure',
  ],
```

- [ ] **Step 3: Typecheck the site**

Run: `cd site && npm run typecheck`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add site/src/pages/roadmap.tsx site/sidebars.ts
git commit -m "docs(site): roadmap + sidebar — lesson 03 available"
```

---

## Task 12: Site — lesson page `site/docs/03-selective-disclosure.mdx`

Follows the five-beat spine with code-imports from the real, tested files. Word counts are targets, not hard limits. Use the **same MDX patterns** as `02-mandates.mdx`: frontmatter, `import Term from '@site/src/components/Term';`, fenced `reference` code-imports of whole files.

**Files:**
- Create: `site/docs/03-selective-disclosure.mdx`

- [ ] **Step 1: Create `site/docs/03-selective-disclosure.mdx`**

```mdx
---
slug: selective-disclosure
title: 03 · Selective disclosure (SD-JWT & key binding)
sidebar_position: 4
---

import Term from '@site/src/components/Term';
```

Then write ~1000–1400 words across the five beats. Required content per beat:

- **## Frame** — Open the box deferred in Lesson 02. Why selective disclosure matters: data minimization (PCI / privacy — the verifier sees only what it needs to decide). Introduce the trust model — `<Term id="issuer-holder-verifier">issuer → holder → verifier</Term>` — and the three vocabulary words: `<Term id="disclosure">disclosure</Term>`, `<Term id="cnf">cnf</Term>`, `<Term id="kb-jwt">KB-JWT</Term>`. Forward-reference: this is exactly what the jwt.io "enter public key manually" prompt from Lesson 02 was reaching for — the holder's key in `cnf` *is* the key resolution.

- **## Build** — Two short paragraphs of theory ("a disclosure is `[salt, name, value]` base64url-encoded; its SHA-256 lands in `_sd`. A KB-JWT covers the whole presentation up to itself via `sd_hash`."), then code-imports in order:
  ````
  ```py reference title="ap2_shared/sdjwt.py"
  ../../ap2_shared/sdjwt.py
  ```
  ````
  ````
  ```py reference title="lessons/03-selective-disclosure/build_sdjwt.py"
  ../../lessons/03-selective-disclosure/build_sdjwt.py
  ```
  ````
  Walk the reader through `issue_credential` (Bank issues with `cnf=holder_pub`, sd_claims moved to disclosures, hashes in `_sd`) and `hold_and_present` (build the no-KB string, hash it, sign a KB-JWT, attach).

- **## Inspect** — Code-import `verify_sdjwt.py`:
  ````
  ```py reference title="lessons/03-selective-disclosure/verify_sdjwt.py"
  ../../lessons/03-selective-disclosure/verify_sdjwt.py
  ```
  ````
  Explain the **three checks** (authenticity = issuer sig; holder binding = KB sig + `cnf` + `sd_hash`; integrity = each presented disclosure's hash must be in `_sd`) and the four demo cases (Valid → True; Tampered → None; Wrong-key KB → None; Missing KB → None). Close the **jwt.io loop**: `cnf` *is* the key the tool was asking for — no admin toggle, just the holder's bound JWK.

- **## Map** — Code-import `map_to_sdk.py`:
  ````
  ```py reference title="lessons/03-selective-disclosure/map_to_sdk.py"
  ../../lessons/03-selective-disclosure/map_to_sdk.py
  ```
  ````
  Explain that `MandateClient.create()` is `make_sdjwt`, `present()` is `make_kb_jwt + attach_kb`, and `verify()` is our `verify`. Then introduce the AP2 mapping: a bank issues an `<Term id="open-mandate">Open Payment Mandate</Term>` with `cnf` + selectively-disclosable constraints (`AllowedPayees`, `AmountRange`); the Shopping Agent presents to a merchant. Note that the SDK additionally supports **array-element** selective disclosure inside `AllowedPayees.allowed[]` — a refinement we deliberately don't build by hand (out of scope; Lesson 04 explores chains).

- **## Check** — A bulleted list of 3 recall prompts with inline answers:
  - *Where does the verifier get the holder's public key?* (From `cnf` inside the issuer-signed SD-JWT.)
  - *What stops a holder from showing a modified `over_18` value?* (Its hash is fixed in the issuer-signed `_sd` array — change the value, hash mismatches, verifier rejects.)
  - *Why does the KB-JWT include `nonce` and `aud`?* (Binds the presentation to *this* verifier + *this* transaction so it cannot be replayed.)
  Then a "Further reading" line with three links:
  - [RFC 9901 — SD-JWT](https://www.rfc-editor.org/rfc/rfc9901.html)
  - [AP2 SDK `sdjwt` README](https://github.com/google-agentic-commerce/AP2/blob/main/code/sdk/python/ap2/sdk/README.md)
  - [AP2 spec — security & privacy](https://github.com/google-agentic-commerce/AP2/blob/main/docs/ap2/security_and_privacy_considerations.md)

- [ ] **Step 2: Build the site to verify code-imports + links resolve**

Run: `cd site && npm run build`
Expected: success (`SUCCESS Generated static files in "build"`). If a `reference` path errors, fix the relative path to be `../../<file>` from `site/docs/`.

- [ ] **Step 3: Commit**

```bash
git add site/docs/03-selective-disclosure.mdx
git commit -m "docs(site): lesson 03 page (Frame · Build · Map · Inspect · Check) with imported code"
```

---

## Task 13: Final verify + redeploy + push

**Files (verification only — no new files):**
- N/A

- [ ] **Step 1: Full pytest**

Run: `uv run pytest -q -W ignore::DeprecationWarning -o addopts=""`
Expected: PASS — 24 (existing) + ~13 (new in `ap2_shared/test_sdjwt.py`) + ~5 (new in lesson) ≈ **42 passed**.

- [ ] **Step 2: Full site build**

Run: `cd site && npm run build`
Expected: `[SUCCESS] Generated static files in "build".`

- [ ] **Step 3: Redeploy to Vercel**

Run: `npx --yes vercel --prod --yes --scope dfzuluagas-projects`
Expected: `Aliased: https://diegozuluaga.dev` line.

- [ ] **Step 4: Verify the new lesson is live**

Run:
```bash
curl -sS -m 15 -o /dev/null -w "%{http_code}\n" --resolve diegozuluaga.dev:443:76.76.21.21 https://diegozuluaga.dev/ap2/docs/selective-disclosure
```
Expected: `200`.

And confirm the title:
```bash
curl -sS -m 15 --resolve diegozuluaga.dev:443:76.76.21.21 https://diegozuluaga.dev/ap2/docs/selective-disclosure | grep -o "<title[^>]*>[^<]*</title>" | head -1
```
Expected: contains `03 · Selective disclosure`.

- [ ] **Step 5: Push to GitHub**

Run: `git push -u origin lesson-03-sd-jwt`
Expected: branch pushed.

- [ ] **Step 6: Final verification line in the agent's report**

Confirm all three "green" criteria for Lesson 03:
- `pytest`: 42 passed (or close — depends on test counts).
- `npm run build`: SUCCESS.
- `https://diegozuluaga.dev/ap2/docs/selective-disclosure`: 200.

---

## Self-Review

**Spec coverage:**

| Spec section | Implementing task(s) |
| :-- | :-- |
| Hybrid scenario (generic Build, AP2 Map) | Tasks 6, 8, 12 |
| Lean SD-JWT + KB only | Task 2–5 (no recursive/decoy/array — out of scope) |
| Shared primitives in `ap2_shared/sdjwt.py` | Tasks 2–5 |
| Lesson dir `lessons/03-selective-disclosure/` | Tasks 6–9 |
| Five-beat spine on the lesson page | Task 12 |
| Map target `ap2.sdk.sdjwt` + OpenPaymentMandate | Task 8 |
| `make_disclosure / make_sdjwt / build_presentation / make_kb_jwt / attach_kb / verify` | Tasks 2 / 3 / 3 / 4 / 4 / 5 |
| Glossary entries (kb-jwt, cnf, issuer-holder-verifier, disclosure; refresh sd-jwt) | Task 10 |
| Sidebar `selective-disclosure` | Task 11 |
| Roadmap flip 03 → available | Task 11 |
| KB-JWT `typ=kb+jwt` (extension to `make_jwt`) | Task 1 |
| KB `sd_hash` covers full presentation-up-to-KB | Task 4 (impl) + Task 5 (verifier checks) |
| DoD: pytest green / npm build / live URL / branch pushed | Task 13 |

**Placeholder scan:** None. All function signatures, file paths, test code, demo expected outputs, and commit messages are concrete. The MDX prose has required-content bullet lists with exact `<Term>` ids, code-import paths, and recall-prompt answers — not "write lesson here."

**Type/name consistency:** verified — `make_disclosure`, `make_sdjwt(sd_claims, issuer_priv, issuer_kid, holder_pub)`, `build_presentation(sdjwt_token, disclosures, reveal)`, `make_kb_jwt(presentation_no_kb, aud, nonce, holder_priv, holder_kid, now=None)`, `attach_kb(presentation_no_kb, kb_jwt)`, `verify(presentation, issuer_pub, expected_aud, expected_nonce)` are used identically across the primitives, lesson code, and tests. Lesson helpers `issue_credential` and `hold_and_present` match between `build_sdjwt.py` and the tests. SDK names (`MandateClient.create / present / verify`, `OpenPaymentMandate`, `PaymentMandate`, `AmountRange`, `AllowedPayees`, `Merchant`, `Amount`, `PaymentInstrument`) match the SDK source.
