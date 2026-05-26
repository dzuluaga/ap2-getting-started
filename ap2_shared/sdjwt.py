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
