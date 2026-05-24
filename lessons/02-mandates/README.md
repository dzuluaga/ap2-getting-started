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
