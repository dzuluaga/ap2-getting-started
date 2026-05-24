"""EC P-256 keypair generation for AP2 lessons."""
from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import ec


def generate_p256_keypair():
    """Return (private_key, public_key) on the NIST P-256 curve (ES256)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()
