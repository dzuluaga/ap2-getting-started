# AP2 from First Principles — Design Spec

**Date:** 2026-05-24
**Status:** Approved (ready for implementation planning)
**Author:** Diego Zuluaga (with Claude)

## Purpose

A public, incremental learning resource that teaches the **Agent Payments
Protocol (AP2)** from first principles. It exists to:

1. Teach the author AP2 deeply — the protocol mechanics *and* the vocabulary,
   well enough to speak intelligently about the agentic-payments industry.
2. Serve as a public showcase others can learn from (a "this is how to get
   started" record).
3. Become a base that grows over time — future work is "add capability X to
   lesson Y" against a stable, consistent structure.

## Audience & calibration

The author has deep adjacent experience (A2A, ACP, UCP, x402, agentic commerce,
and substantial identity / verifiable-credentials / mDL work). "First
principles" here means **rigorous conceptual grounding** (mandates, signing,
roles, trust, selective disclosure) — not beginner programming hand-holding.

## Core decisions (locked)

| Decision | Choice |
| :-- | :-- |
| Learning approach | **Hybrid build-then-map**: for each capability, build a minimal from-scratch version that exposes the mechanics, then map it to the official AP2 SDK + spec. |
| Publishing | **Docusaurus → Vercel** (sequential lesson sidebar, blog for narrative, search, glossary). |
| Repo structure | **Monorepo, code-as-source-of-truth**: runnable/tested lesson code in `lessons/`, Docusaurus in `site/` importing real snippets from the lesson code. Single Vercel deploy. |
| v1 scope | **Foundations only** — site live + Lessons 00–02. |
| Language/stack | Python 3.11+ with `uv` (matches AP2); Docusaurus + TypeScript. |

## AP2 grounding (as of the current cloned `../AP2`)

The curriculum must use current, faithful terminology. Key facts:

- **Roles:** Shopping Agent (SA), Credential Provider (CP), Merchant (M),
  Merchant Payment Processor (MPP), Trusted Surface (TS), Network & Issuer.
- **Mandates:** **Checkout Mandate** (authorizes completing a checkout) and
  **Payment Mandate** (authorizes the payment). Mandates can be **Open** (not
  yet bound to a specific action; carries constraints) or **Closed** (bound to a
  specific action/verifier). A **Mandate Receipt** is a verifier-signed JWT with
  the result of action authorization.
- **Two core journeys:** **Human-Present (HP)** and **Human-Not-Present (HNP)**.
- **Trust foundation:** SD-JWT (selective disclosure JWT) + key binding;
  "verifiable intent, not inferred action"; privacy/PCI data minimization via
  selective disclosure; dynamic linking; Strong Customer Authentication (SCA).
- **Ecosystem:** AP2 is designed as an extension over A2A / MCP / UCP; related to
  x402.
- **Terminology evolution worth teaching:** earlier AP2 used Intent/Cart/Payment
  mandates; the current model uses Checkout/Payment with Open/Closed states.

### Dependency story (verified)

The official `ap2` SDK is **not published on PyPI**. It is git-installable:
`ap2 @ git+https://github.com/google-agentic-commerce/ap2.git` (repo-root
package; `setuptools` finds packages under `code/sdk/python`). Its own deps
include `cryptography`, `jwcrypto`, `pydantic`, and the published `sd-jwt` lib.
We pin to a specific commit for reproducibility so web learners get a stable
build (no local-path dependencies).

Two dependency tiers in our `pyproject.toml`:

- **Low-level** (`cryptography`, `jwcrypto`) — for the from-scratch "Build" step.
- **Official `ap2` SDK** (git-pinned) — for the "Map" step.

## Architecture & repo layout

```
ap2-getting-started/
├── README.md                  # what this is · how to run a lesson · live site link
├── pyproject.toml             # uv-managed Python workspace for all lessons
├── vercel.json                # deploy: build site/
├── scripts/new-lesson.py      # scaffolds a new lesson from the template
├── lessons/
│   ├── _template/             # canonical lesson skeleton (README + code + test)
│   ├── 00-why-agent-payments/ # concept lesson (tiny "trust gap" illustration)
│   ├── 01-roles-and-flow/     # the six roles + two journeys, as runnable stubs
│   └── 02-mandates/           # build Checkout+Payment mandate (plain signed JWT) → map to SDK
│       ├── README.md
│       ├── build_mandate.py
│       ├── verify_mandate.py
│       ├── map_to_sdk.py
│       ├── run.sh
│       └── test_mandates.py
└── site/                      # Docusaurus (TypeScript)
    ├── docs/                  # lesson MDX (narrative; imports code from ../lessons)
    ├── blog/                  # narrative posts + terminology deep-dives
    ├── src/data/glossary.ts   # AP2 terms we teach → /glossary page + tooltips
    ├── docusaurus.config.ts
    └── sidebars.ts
```

Snippet sync via `remark-code-import`: every code block on the site references
real files under `lessons/`, so a renamed/broken snippet fails the site build —
keeping prose and tested code honest.

## The learning framework — repeatable lesson spine

Every lesson follows the same five beats. This consistency *is* the "step by
step framework," and it makes future lessons predictable to author.

1. **Frame** — the problem this concept solves + the exact AP2 **vocabulary**
   introduced (glossary definition + plain-English gloss + how the industry uses
   the term).
2. **Build** — minimal, dependency-light code *you* write that exposes the
   mechanic. Runnable.
3. **Map** — connect what you built to the official `ap2` SDK + the precise spec
   section (and related protocol: A2A / MCP / UCP).
4. **Inspect** — print/decode the real artifacts (decoded SD-JWT, mandate JSON)
   so the bytes are visible, including a **negative test** (tamper → verification
   fails) that demonstrates what the protocol protects.
5. **Check** — 2–3 recall prompts ("you can now explain X") + spec references.

Enforced by `lessons/_template/` + `scripts/new-lesson.py`.

## Full lesson roadmap

Published as a `/roadmap` page. v1 = lessons 00–02; the rest are scaffolded as
"coming soon."

| # | Lesson | In v1? |
| :-- | :-- | :-- |
| 00 | Why agent payments? — the trust/liability gap; verifiable intent vs inferred action | ✅ |
| 01 | The cast & the journeys — SA, CP, Merchant, MPP, Trusted Surface, Network/Issuer; HP vs HNP | ✅ |
| 02 | Mandates, the unit of trust — Checkout + Payment Mandate; Open vs Closed; build by hand as a **plain signed JWT** (SD-JWT internals deferred to 03) → map to SDK | ✅ |
| 03 | Selective disclosure: SD-JWT & key binding (issuer–holder–verifier; PCI/privacy minimization) | — |
| 04 | Mandate chains & receipts; dynamic linking & SCA | — |
| 05 | Human-Present happy path, end-to-end (mocked SA/M/CP + Trusted Surface consent) | — |
| 06 | Human-Not-Present & autonomous delegation (Open→Closed, "buy when price < $X", constraints) | — |
| 07 | Riding on A2A (AP2 as an A2A extension; run the official scenario) | — |
| 08 | AP2 vs/with MCP, UCP, x402 (situate it in the ecosystem) | — |
| 09 | Action authorization, disputes & liability | — |

**Sequencing note:** each lesson introduces exactly one new idea. Lesson 02
establishes the mandate *data model* and signs it as a plain JWT, treating the
signature as a black box; Lesson 03 then opens that box (SD-JWT selective
disclosure + key binding). The Lesson 02 "Map" step notes that the SDK wraps
mandates as SD-JWTs, forward-referencing Lesson 03.

## v1 — definition of done

- Docusaurus site themed and **deployed to Vercel**, with: landing page,
  `/glossary`, `/roadmap`, and a sidebar listing lessons 00–02.
- Lessons 00–02 written to the five-beat spine.
- Lesson 02 ships runnable, **pytest-passing** code (`build_mandate.py`,
  `verify_mandate.py`, `map_to_sdk.py`, `run.sh`).
- Blog post #1: "Learning AP2 from first principles."
- `README.md` (run instructions + live link) and a working
  `scripts/new-lesson.py`.
- **Green means:** `pytest` passes, `npm run build` (site) passes, and the
  Vercel URL is live.

## Tooling

- **Python:** 3.11+, `uv` workspace. Deps split into low-level (build) and
  official `ap2` SDK (map). `pytest` for tests.
- **Site:** Docusaurus + TypeScript, `remark-code-import`, deployed via Vercel.
- **Glossary:** seeded from AP2's official glossary for terms we teach; rendered
  as `/glossary` plus inline term tooltips in lessons.
- **CI** (GitHub Actions: pytest + site build) is noted as a *future* add, not
  part of v1.

## Out of scope for v1 (explicitly deferred)

- Lessons 03–09 (scaffolded as "coming soon" only).
- End-to-end multi-agent flows, A2A wiring, HNP autonomy.
- CI pipeline.
- Custom domain (use the default Vercel URL for v1).
```
