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
- `sdjwt_to_sdk.py` — the same flow via `ap2.sdk.sdjwt` + an AP2 `OpenPaymentMandate` example.

The full narrative lives on the site: **/docs/selective-disclosure**.
