# Lesson 02 — Mandates, the unit of trust

Build a **Checkout Mandate** and a **Payment Mandate** by hand, then map them to
the official `ap2` SDK models.

## Run

```bash
bash run.sh            # build → verify → map
uv run pytest lessons/02-mandates -q
```

## Files
- `build_mandate.py` — build the mandates (merchant-signed cart as a plain JWT); prints each signer's public key as a JWK.
- `verify_mandate.py` — verify the signature **and** the cart hash (tamper test).
- `map_to_sdk.py` — the same data as `ap2.models.mandate.CartMandate` / `PaymentMandate`.

## Verify a token in jwt.io
`build_mandate.py` prints each token next to its public key (JWK). At
[jwt.io](https://jwt.io), paste the JWT, then — when it asks you to enter the
key manually (the `iss` is the placeholder `"user"`) — paste the matching JWK
from the same run and pick **ES256**. Token and key must be from the same run
(keys are ephemeral).

The full narrative lives on the site: **/docs/mandates**.
