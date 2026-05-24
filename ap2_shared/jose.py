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
    """Return the payload if the ES256 signature is valid, else None.

    Always verifies with ES256 and the supplied key. The `alg` field in the
    header is NOT checked — intentional for teaching clarity. A production
    library must reject tokens whose `alg` does not match the expected
    algorithm, otherwise it is open to algorithm-confusion attacks.
    """
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
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError(f"Expected 3 JWT segments, got {len(parts)}")
    _, encoded_payload, _ = parts
    return json.loads(b64url_decode(encoded_payload))
