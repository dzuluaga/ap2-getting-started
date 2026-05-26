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
