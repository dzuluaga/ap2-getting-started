# Lesson 03 — Selective disclosure (SD-JWT & key binding): Design Spec

**Date:** 2026-05-25
**Status:** Approved (ready for implementation planning)
**Author:** Diego Zuluaga (with Claude)

## Purpose

Open the SD-JWT black box that Lesson 02 deliberately deferred. Build an
**issuer → holder → verifier** flow with **selective disclosure** and **key
binding (KB-JWT)** by hand on top of `ap2_shared.jose`, then map it to
`ap2.sdk.sdjwt` and show this is precisely the pattern AP2 uses for **Open
Payment Mandates** (`OpenPaymentMandate` + `cnf` + constraints).

This lesson also closes the open thread from Lesson 02: the jwt.io
"Please enter public key manually" prompt for `iss: user` is exactly the
key-discovery step `cnf` automates in SD-JWT key binding.

## Approved decisions

| Decision | Choice |
| :-- | :-- |
| Scenario framing | **Hybrid** — generic identity-credential example in **Build**; AP2 `OpenPaymentMandate` example in **Map**. |
| Scope of the from-scratch build | **Lean SD-JWT + KB-JWT** — object-level selective disclosure + key binding. Skip recursive disclosures, decoy digests, array-element disclosure. |
| Shared primitives location | **`ap2_shared/sdjwt.py`** — same pattern as `ap2_shared/jose.py`, so future lessons (04+) reuse it. |
| Lesson dir | `lessons/03-selective-disclosure/` |
| Slug | `selective-disclosure` |
| Map target | `ap2.sdk.sdjwt.sd_jwt` + `ap2.sdk.sdjwt.kb_sd_jwt` (and an AP2 `OpenPaymentMandate` example for the Map beat). |
| Lesson template | The established **five-beat spine** (Frame · Build · Map · Inspect · Check). |
| Tests | TDD; full pytest suite stays green. |

## Vocabulary the lesson introduces / refines

Refresh in `site/src/data/glossary.ts`:

- **`sd-jwt`** (refresh short text — make it concrete about disclosures + `_sd` hashes).
- New: **`kb-jwt`** — Key-Binding JWT signed by the holder for a specific verifier/transaction (`typ=kb+jwt`, with `aud`, `nonce`, `iat`, `sd_hash`).
- New: **`cnf`** — confirmation claim in an SD-JWT carrying the holder's public key (`{cnf: {jwk: ...}}`); this is the bound key.
- New: **`issuer-holder-verifier`** — the three-party trust model SD-JWT formalizes.
- New: **`disclosure`** — `[salt, name, value]` triple, base64url-encoded; included only when the claim is revealed.

## Five-beat spine (Hybrid scenario)

- **Frame.** Why selective disclosure: PCI/privacy data minimization — verifier sees only what it needs. The three roles: `<Term id="issuer-holder-verifier">issuer → holder → verifier</Term>`. The puzzle from Lesson 02: how does a verifier even *get* the right key for `iss`? Answer: `<Term id="cnf">cnf</Term>` + `<Term id="kb-jwt">KB-JWT</Term>`. Source: RFC 9901, AP2 spec §security & privacy.

- **Build (generic).** A bank issues a credential to a user with claims `{name, country, account_id, over_18, account_tier}`, all selectively disclosable. The user presents to a merchant revealing only `country` and `over_18`, with a KB-JWT proving holder binding for *this* transaction (`aud=merchant`, `nonce`). Show:
  - Building one `<Term id="disclosure">disclosure</Term>` (salt + name + value, base64url-encoded).
  - Computing its hash and putting that hash in the issuer-signed SD-JWT's `_sd` array (clear payload no longer contains the value).
  - The wire format: `<SD-JWT>~<disclosure1>~<disclosure2>~...~<KB-JWT>~`.

- **Inspect.** Decode the wire format. Show: `_sd` contains *all* claim hashes (even ones not revealed → verifier *knows* something existed but can't see it); the holder controls the disclosures they include. Run the verifier through four cases — valid → `True`; tampered disclosure → `False` (hash mismatch); wrong holder key on KB → `False` (signature fail); missing KB when `aud/nonce` expected → `False`. Explicitly close the **jwt.io loop**: the bound `cnf` key *is* the key resolution the tool was asking for.

- **Map.** Same flow via `ap2.sdk.sdjwt` (`sd_jwt.create` + `kb_sd_jwt.create` + `chain.verify_chain`). Then the AP2-flavored example: issue an `OpenPaymentMandate` with constraints (`AllowedPayees`, `AmountRange`), `cnf` bound to the Shopping Agent's key; the agent presents disclosing only the constraints the verifier needs, with a KB-JWT for `aud=merchant`. This is exactly the pattern from the SDK README's "Example."

- **Check.** Recall prompts:
  1. *Where does the verifier get the holder's public key?* (from `cnf` in the SD-JWT.)
  2. *What stops a holder from showing a modified `over_18` value?* (its hash is fixed in the issuer-signed `_sd` array.)
  3. *Why does the KB-JWT include `nonce`/`aud`?* (binds the presentation to *this* verifier + transaction → not replayable.)
  References: RFC 9901, `ap2/code/sdk/python/ap2/sdk/sdjwt/README.md`, AP2 spec.

## From-scratch primitives — `ap2_shared/sdjwt.py`

Built on top of `ap2_shared.jose` (`make_jwt`, `verify_jwt`, `b64url_encode/decode`, `canonical_json`, `sha256_b64url`, `public_jwk`). All function names, return types, and behavior are fixed by this spec.

| Function | Signature | Behavior |
| :-- | :-- | :-- |
| `make_disclosure` | `(name: str, value, salt: str \| None = None) -> tuple[str, str]` | Builds one disclosure. Generates (or accepts) a 16-byte random salt encoded base64url. Serializes `[salt, name, value]` with `json.dumps(..., separators=(",", ":"))` and base64url-encodes that JSON. Returns `(disclosure_b64url, hash_b64url)` where `hash_b64url = sha256_b64url(disclosure_b64url.encode("ascii"))`. |
| `make_sdjwt` | `(*, payload: dict, sd_claims: list[str], issuer_priv, issuer_kid: str, holder_pub=None) -> tuple[str, dict[str, str]]` | For each key in `sd_claims`, builds a disclosure (via `make_disclosure`) and removes the key from the clear payload. Adds `_sd: [hash, ...]` to the clear payload (always present, possibly empty). If `holder_pub` is given, adds `cnf: {jwk: public_jwk(holder_pub)}`. Signs the resulting clear payload as an ES256 JWT (`make_jwt`). Returns `(sdjwt_token, {claim_name: disclosure_b64url})`. |
| `build_presentation` | `(*, sdjwt_token: str, disclosures: dict[str, str], reveal: list[str]) -> str` | Returns the compact wire string up to (but not including) any KB-JWT: `<sdjwt>~<disc_i>~<disc_j>~...~` — only disclosures for claim names in `reveal`, in `reveal`'s order. Always ends with `~`. |
| `make_kb_jwt` | `(*, presentation_no_kb: str, aud: str, nonce: str, holder_priv, holder_kid: str, now: int \| None = None) -> str` | Computes `sd_hash = sha256_b64url(presentation_no_kb.encode("ascii"))` and signs a KB-JWT with header `typ=kb+jwt` and payload `{aud, nonce, iat: now or int(time.time()), sd_hash}`. `now` is injectable so tests are deterministic. |
| `attach_kb` | `(presentation_no_kb: str, kb_jwt: str) -> str` | Returns `presentation_no_kb + kb_jwt + "~"`. |
| `verify` | `(*, presentation: str, issuer_pub, expected_aud: str \| None = None, expected_nonce: str \| None = None) -> dict \| None` | (1) Splits the wire format on `~`. (2) Verifies the SD-JWT signature with `issuer_pub`. (3) **If a KB-JWT is present, always** verifies its signature against the key in the SD-JWT's `cnf.jwk` *and* that `sd_hash` equals `sha256_b64url(presentation_no_kb.encode("ascii"))`. (4) If `expected_aud` / `expected_nonce` is provided, requires a KB-JWT and checks the claims match. (5) Rebuilds the revealed-claims dict by hashing each presented disclosure and matching against `_sd` (unmatched disclosures → failure). Any failure → `None`. |

## Wire format (the lesson exposes this directly)

```
<base64url(header).base64url(payload).base64url(sig)> ~ <disc1> ~ <disc2> ~ ... ~ [<kb-jwt>] ~
```

- Tildes (`~`) separate the SD-JWT, the included disclosures, and the optional trailing KB-JWT.
- A presentation **always ends** with `~` (whether or not KB is present).
- Disclosures are the base64url-encoded `[salt, name, value]` strings; their order doesn't matter to the verifier (it hashes whatever is presented and matches against `_sd`).
- The KB-JWT's `sd_hash` covers **everything before** the KB (SD-JWT + included disclosures + the trailing `~`), so the verifier knows exactly which disclosures the holder intended to present — swap any of them and the KB no longer matches.

## Lesson code (mirrors L02 layout)

```
lessons/03-selective-disclosure/
├── README.md            # pointer to /docs/selective-disclosure + run instructions
├── build_sdjwt.py       # issuer issues a credential; holder presents selectively
├── verify_sdjwt.py      # verify_presentation() + main() demoing 4 failure modes
├── map_to_sdk.py        # same flow via ap2.sdk.sdjwt + an AP2 OpenPaymentMandate example
├── run.sh               # build → verify → map
└── test_sdjwt.py        # TDD tests (issue+present roundtrip; selective disclosure; tamper; wrong-key KB; missing-KB)
```

The generic Build values (used in `build_sdjwt.py` + tests):

| Field | Value |
| :-- | :-- |
| Issuer | `"Bank of Examples"` (`iss`) |
| Subject | `"user_alice"` (`sub`) |
| Selectively-disclosable claims (`sd_claims`) | `name`, `country`, `account_id`, `over_18`, `account_tier` |
| Reveal subset (in the demo presentation) | `country`, `over_18` |
| Verifier | `aud="merchant.example"` |
| Nonce | `"txn-001"` |

The Map AP2 example uses `OpenPaymentMandate` with two constraints (`AmountRange` USD 0–5000 and `AllowedPayees` for one merchant), `cnf` = agent's public key, then the agent presents — first revealing both constraints, then only the AmountRange — both should verify.

## Site changes (Docusaurus)

- New page `site/docs/03-selective-disclosure.mdx` — five-beat spine, code-imports from `ap2_shared/sdjwt.py` and the three lesson files, `<Term>` usages.
- `site/sidebars.ts` — append `'selective-disclosure'` to the `lessons` sidebar.
- `site/src/data/glossary.ts` — add `kb-jwt`, `cnf`, `issuer-holder-verifier`, `disclosure`; refresh `sd-jwt`.
- `site/src/pages/roadmap.tsx` — flip lesson 03 from "coming soon" to ✅ available.

## Definition of done

- `uv run pytest -W ignore::DeprecationWarning -o addopts="" -q` is green (target: existing 29 tests **plus** new ones from `ap2_shared/test_sdjwt.py` and `lessons/03-selective-disclosure/test_sdjwt.py`).
- `bash lessons/03-selective-disclosure/run.sh` prints, in order: a successfully verified presentation (`True`), then three demonstrated failure modes (`False`).
- `cd site && npm run build` succeeds with `onBrokenLinks: 'throw'`.
- Lesson live at `https://diegozuluaga.dev/ap2/docs/selective-disclosure` (200).
- Code-imports on the lesson page resolve to the real `ap2_shared/sdjwt.py` and lesson files.
- Roadmap page shows lesson 03 as ✅ available.
- Branch merged to `main` and pushed to GitHub.

## Explicitly out of scope (deferred to later lessons)

- **Recursive disclosures** (a disclosure whose value is itself an SD-JWT-style nested object with its own `_sd`). Real but not needed for the teaching point.
- **Decoy digests** (extra fake hashes in `_sd` to obscure the count of unrevealed claims).
- **Array-element selective disclosure** (`...` placeholders inside arrays). The AP2 SDK uses this for `AllowedPayees.allowed[]` — we acknowledge in the Map beat that the SDK does it, but don't build it from scratch here.
- **Mandate chains** (`~~`-joined multi-hop dSD-JWT) → Lesson 04.
- **Receipts** → Lesson 04.
