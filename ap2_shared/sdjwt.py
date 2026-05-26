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
