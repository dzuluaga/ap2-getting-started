# AP2 from First Principles

A public, incremental resource for learning the **Agent Payments Protocol (AP2)**
by building it by hand, then mapping each piece to the official `ap2` SDK.

**Live site:** https://diegozuluaga.dev/ap2

Each lesson follows the same five-beat spine: **Frame · Build · Map · Inspect ·
Check**. Every code snippet on the site is real, tested code imported straight
from this repo.

## Layout
- `lessons/NN-slug/` — runnable, tested lesson code.
- `ap2_shared/` — shared, installable JOSE primitives (from-scratch ES256 JWTs).
- `site/` — Docusaurus site (imports real snippets from the lessons).
- `docs/superpowers/` — the design spec and implementation plan.

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

## Lessons (available)
- **00 — Why agent payments?** the trust/liability gap; verifiable intent.
- **01 — The cast & the journeys** the six roles; Human-Present vs Human-Not-Present.
- **02 — Mandates, the unit of trust** build Checkout + Payment mandates, then map to the SDK.
- **03 — Selective disclosure (SD-JWT & key binding)** build issuer–holder–verifier with selective disclosure + KB-JWT, then map to `ap2.sdk.sdjwt` and the AP2 `OpenPaymentMandate` pattern.

See the full roadmap on the site.

## Conventions
Each lesson's "map to SDK" file is **lesson-named** (`mandates_to_sdk.py`-style — except L02 keeps the original `map_to_sdk.py` for historical reasons; L03 uses `sdjwt_to_sdk.py`). This avoids `sys.modules` collisions when pytest runs tests across multiple lesson dirs (the lesson dir names contain hyphens, so they can't be Python packages).
