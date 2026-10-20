# Refinement: SAOSA multi-branch readiness — is this blueprint only for Outeniqua?

**Status:** Refinement — findings recorded 2026-10-19; no build approved. Awaits a product decision on deployment shape (§8) and the four leaks in §5.
**Owner:** Kobus Meiring (Product)
**Last Updated:** 2026-10-19
**Scope:** Whether this codebase can serve **other PGS groups under SAOSA / PGS SA**, not only
Outeniqua, and what it would cost. **Not in scope:** runtime multi-tenancy (§8 shape ii is
recommended *against*), and the field app's offline architecture (`1b`, unchanged).
**Reference:**
- `PGS_PLATFORM_SPEC.md` §4.8 (code vs data), §IX-equivalent in
  `product/docs/context/build_principles.md` §IX (single-tenant blueprint), D12, D16, D41
- `product/docs/context/build_principles.md` §I, §IV, §IX
- `pgs_docs/saoso-version-2.1-2026.pdf` Section C Appendices A–C (the national PGS criteria)
- `pgs_docs/PGS Certification landscape_Final.pdf` (PGS SA's own framing)
- `core/services/_public.py`, `core/services/_seed.py`, `core/services/_documents.py`,
  `core/services/_chatbot.py`, `knowledge/sections/__init__.py`

> **Written with another agent live in the tree.** This file is new and touches nothing else.
> Two consequences recorded for whoever commits: (1) `product/backlog/backlog.md` is
> generated — do not hand-edit it; run `python product/backlog.py --write` when the tree is
> quiet. (2) **`D45` is currently allocated twice** — by `ready/CORPUS_COLUMN_EXTRACTION_PRD.md`
> §9 (corpus layout) and by `ready/MVP1A_PRD.md` §5.8 (Sheet I conclusion). This document
> therefore proposes **D46** and leaves D45 to be resolved between those two owners.

---

## 1. The question

Outeniqua PGS is one group among SAOSA / PGS SA's member groups. If another branch wants to
use this platform, what actually has to change — settings and seed data, or code?

§4.8 already claims the answer for *retargeting to another standard or PGS group*: seeds,
corpora, questionnaires and seals are data, and "no model changes, no migrations, no new
services". That claim was written for a standard swap (SAOSO v2.1 → EU 2018/848 → IFOAM
COROS). It was **never tested against a second branch of the same national scheme**, which is
the cheaper and more likely case.

## 2. Finding 1 — only one of eight source documents is group-owned

Occurrence count of `outeniqua` (case-insensitive) in `pdftotext` output of every file in
`pgs_docs/`:

| Source document | `outeniqua` hits | Owner |
|---|---|---|
| `saoso-version-2.1-2026.pdf` | 0 | SAOSO — national |
| `6. PGS Farm visit assessment form …summary_2026.xlsx` (the FORM) | 0 | **PGS SA — national** |
| `Basic Production Principles_ENG_PRINT.pdf` | 0 | PGS SA — "Growing the organic sector in South Africa" |
| `PGS Certification landscape_Final.pdf` | 0 | PGS SA — national |
| `5. PGS Farm Visit preparation list.pdf` | 0 | PGS SA — national |
| `7.a` / `7.b` / `7.c` participant checklists | 0 | PGS SA — national |
| `Outeniqua pgs principles, policies and procedures 2026.pdf` (the OPP) | **14** | **Outeniqua only** |

Reproduce: `for f in pgs_docs/*.pdf; do pdftotext -q "$f" - ; done | grep -ci outeniqua`
(per file, as done above).

The FORM's own headers confirm it: *"6. PGS Application, Questionnaire and Assessment Form"*,
referring to **PGS SA**, **PGSSA**, **SAOSO** and *"the group's chosen organic standard"* — it
is deliberately written to be group-neutral, and the numbered prefixes `5.`, `6.`, `7.a–c`
are a national document set, not an Outeniqua one.

**Consequence, and it is the most valuable single fact in this document:** the questionnaire
is national. All 38 Crops questions, the Sheet A–J structure, the `V#` refs and the polarity
work of D27 are shared by every branch. One authoring effort serves the whole country; a
branch's `AssessmentTemplate` should differ by `version`, never by content.

**The counterweight:** that authoring effort is not finished. B3's second-reader sign-off on
the Crops template (38 questions, 37 verdicts, by hand) is still outstanding
(`HANDOVER.md` §3), and D28 chose hand-authoring over extraction. A branch inherits an
unverified template — which is why the corpus column-extraction work in `ready/` matters
nationally, not just locally.

## 3. Finding 2 — the process we already model is the national PGS process

`SAOSO v2.1 Section C, Appendix B — Criteria for Approval of PGS` is a 14-point national
definition of a legitimate PGS. Mapping it against the code:

| Appendix B criterion | Modelled? | Where |
|---|---|---|
| (a) participatory structure, elected reps, decisions in assembly | ✅ | `Role`/`UserRole` (`_core.py`), committee (MVP 2) |
| (b) locally adapted, minimal paperwork | ✅ | the connect-the-dots premise of the PWA |
| (c) public pledge + on-site review at least yearly | ✅ | pledge (1a), `FarmVisit.next_visit_due` |
| (d) non-compliance system with consequences incl. suspension | ✅ | `CorrectiveAction` `ESCALATED`, `Certificate.status` |
| (e) open access to standard, member list, endorsed list, procedures | ✅ | the public site **is** this: `/documents/`, `/members/`, `/how-it-works/` |
| (f) producers understand principles, rights, sanctions | ✅ | knowledge-exchange narrative, visit report |
| (g) team ≥3, 1 experienced + 1 peer operator, **reciprocal assessment invalid** | ✅ | `validate_assessment_team()` (1a) |
| (h) external non-compliance intake ("social control", complaints) | ❌ | nothing |
| (i) decision by the group itself, conflict-of-interest control | ⏳ | MVP 2 committee |
| (j) compliance record per producer, updated yearly | ✅ | assessments + verdicts |
| (k) recognition/market access to endorsed producers only | ✅ | `Seal` / `Certificate` (MVP 2) |
| (l) open gate, observers, consumer members | ✅ | `Role.CONSUMER`, membership classes |
| (m) procedures reviewed at least every 2 years | ❌ | nothing |
| (n) yearly capacity building / knowledge sharing | ❌ | nothing |

**Eleven of fourteen are already modelled**, one is MVP 2, and the three gaps are calendar
and intake items, not schema. This is the strongest available answer to "are we broad enough":
the branch-portable part of this platform is not a hopeful abstraction, it is the national
criteria being implemented by accident because they are what a PGS *is*.

## 4. Finding 3 — the umbrella half of the national standard is missing from the corpus

D41 scoped the corpus to SAOSO **Section B** (p23–p89) because SAOSO's numbering is part-local
and Section A collides with itself. That was correct for MVP 0's job (FORM verdicts cite only
Section B clauses). It is the wrong scope for a *branch* deployment, because:

- **Section A** holds the principles, the definitions, and the regulatory minimum.
- **Section C Appendix A** holds the **two national logos**: the third-party organic logo and
  the *PGS-endorsed* logo.
- **Section C Appendix B** holds the criteria in §3 above.
- **Section C Appendix C** holds the **approval procedure**: a group must be approved by
  PGSSA, initial approval valid **1 year**, subsequent **2 years**, re-submission one month
  before expiry, SAOSO holding a right of veto.

Cost to add, per D41's own note: a `part` discriminator on `DocumentChunk` plus a Section A
sub-document discriminator, and a citation scheme for appendices (`Appendix B.a`). **That is a
migration** — the only known place where D12's "a retarget must not require a migration"
acceptance test breaks. It is already declared as a recorded gap, not silently ignored. It
should be its own PRD; it is not smuggled into this one.

Why it matters beyond the chatbot: if a branch's legitimacy is ever to be *shown* rather than
asserted ("this group is PGSSA-approved until X"), that is a `GroupApproval` row with a
validity window and a state machine, and Appendix C is its specification.

## 5. The four leaks — group data still living in code

These are the actual retarget cost today. All four are the failure mode §4.8 exists to prevent.

| # | Leak | Evidence | Fix shape | Size |
|---|---|---|---|---|
| **L1** | **Fee schedule is a code constant.** OPP §2.1/§2.3 figures, six turnover bands, are Python in a service | `core/services/_public.py:67` `MEMBERSHIP_FARMER_CENTS = 10_000`, `:70` `MEMBERSHIP_PGS_SA_CENTS = 50_000`, `:74` `FEE_BANDS` (6 rows), consumed at `:255–256`. The docstring states *"MVP 1 replaces it with `AssessmentFee` rows (D29)"* | Keep the `FeeBand` shape, move the values into `seed_deployment` / a deployment settings block. §4.8 lists "fee bands" as per-deployment data explicitly | Small. **The one genuine §4.8 violation in the tree** |
| **L2** | **A seal cannot say whose claim it is.** `Seal` records `standard_ref` but no issuing authority, so a national mark and a group mark are indistinguishable rows | `core/models/_certification.py:36` (`Seal`); fields `code`/`label`/`standard_ref`/`is_active`/`criteria_defined`/`display_note`. SAOSO issues **two logos nationally** (Section C App A); the OPP §V adds **three** of its own (`_seed.py:79`) | Add `issuer` and optional `scope` as `CharField` with **no `choices=`** — same rule as `Seal.code`. Claim discipline then distinguishes "SAOSO PGS endorsed" from "Outeniqua seal" | Small, and it is shared with the regenerative add-on (see `REGENERATIVE_ADDON_ARCHITECTURE.md` §6) |
| **L3** | **Group identity has no home at all**, and one string is pinned by a test | 9 templates contain "Outeniqua" (`base.html` `og:site_name`, `_header.html`, `_footer.html` ×4 incl. `footer__place` "Outeniqua, Western Cape", `_disclaimer.html`, `members.html`, `organics.html`, `home.html`, 2 chatbot panels); `core/services/_public.py` PAGES carry it in every `title`; **`core/services/_chatbot.py:61` `REFUSAL` names "the Outeniqua PGS documents" and is pinned by `core/tests/test_chatbot_grounding.py:69 test_the_refusal_is_the_d17_wording`**; `knowledge/ingest.py:70` hardcodes `issuing_body: "Outeniqua PGS"`. `pgs/settings.py` has **no** group-identity block | Introduce a deployment identity block (name, place, `og:site_name`, footer lines, refusal's document name, default `issuing_body`) with the current values as defaults, so `verify.sh` stays green and a clone changes one file | Medium — content, but the refusal string must move or a clone ships a bot that names Outeniqua |
| **L4** | A branch's own procedures document needs a **new parser module** | `knowledge/sections/__init__.py` registers `saoso` / `opp` / `heading`, selected by data (`StandardDocument.section_scheme`). The `opp` scheme (`knowledge/sections/opp.py`) encodes `V.`, `4.2`, items `1)`, letters `a.` | None needed — a format parser *is* code. Write it down: one module per procedures document a branch brings | One file per branch; acceptable |

L1–L3 are group content in code. L4 is correctly code.

## 6. National material worth ingesting (data only, no architecture)

Named in `PGS Certification landscape_Final.pdf` §"Establishing a PGS group" as the resource set
for a new branch, and **absent from `pgs_docs/`**:

1. *PGS SA: How to set up a PGS group*
2. the **PGS Manual** template (Appendix C §3.2(a) requires one for approval)
3. the **PGS GROUP APPLICATION FORM** template (Appendix C §3.2(b))

Ingesting these is a `StandardDocument` row plus `ingest_standard` (D12), and makes the chatbot
useful to a branch founder rather than only to a branch member. No model change.

## 7. Field app consequence — free, if it is claimed now

The assessor PWA does not exist: `1b` is unbuilt and the `0∥` spike is still open
(`HANDOVER.md` §3). Nothing is owed, and nothing is baked in. Two rules now cost nothing and
are irreversible later:

- **The `visitPack` template arrives as data** (`AssessmentTemplate.schema`), never compiled into
  the JS. A branch's questionnaire is a JSON file, on-device.
- **Group identity in the pack comes from the seed**, not from a string literal in a template or
  a service worker cache name — the cache name and the manifest will otherwise hardcode a group.

## 8. Three deployment shapes — a product decision, not a refactor

| # | Shape | Needs | Verdict |
|---|---|---|---|
| **i** | **Blueprint cloned per branch** — one instance per group, one database each | Only L1–L3 closed. No tenancy, no shared rows. §IX mandating this is why the model layer has no tenant key anywhere | ✅ **Recommended.** Matches `build_principles.md` §IX verbatim, and matches PGS SA's own structure (each group is an independent legal/organisational entity with its own OPP, fees and committee) |
| **ii** | **One instance, all branches, PGSSA as approver** | A group/tenant dimension on every user-owned row, per-group fees, per-group seal sets, per-group corpora, plus the Appendix C approval workflow (1 yr / 2 yr, file review, sample member files, veto) | ❌ **Do not.** Forbidden by §IX; it is a reversal of a documented decision, not a feature. It also creates a data-protection question: one database holding every branch's member PII |
| **iii** | **A national deployment for the public surface + corpus + chatbot**, with per-branch instances for members/visits/field work | 7 of 8 documents are already national; the chatbot touches **no farm data**; `StandardSet` already supports corpora coexisting and `ChatSession` is already pinned to one (`core/models/_chat.py:63`) | ⚠️ **Attractive, worth deciding.** It gets every branch a website and a national knowledge base for the price of seeding. It must be a *separate deployment* with its own settings — not a tenant dimension — and the site must then say "a national resource listing member groups", with membership still not implied to be certification |

**The distinction to keep straight:** the *branch* story needs **data plus one new deployment**.
It does not need a new model dimension. The *regenerative add-on* is the case that needs a
dimension (a second scheme inside one deployment). Do not let the two merge.

## 9. Execution steps, smallest first

1. **L1 — fees out of code.** Move the OPP §2.1/§2.3 figures into the deployment seed/identity
   block; keep `FeeBand`'s shape and the existing tests' assertions intact by asserting against
   the seeded rows rather than the constants.
2. **Proposed D46 — deployment identity block.** Group name, place, `og:site_name`, footer
   lines, chatbot's document name (the D17 refusal keeps its wording as the shipped default),
   default `issuing_body`, fee bands, catchment. One settings module; every template and the
   refusal read from it.
3. **L2 — `Seal.issuer` / `Seal.scope`.** Seed SAOSO's two national logos (Section C App A) as
   rows with `issuer="SAOSO/PGSSA"` and `is_active=False` until an approval mechanism exists;
   keep the OPP §V three as `issuer="Outeniqua PGS"`. No `choices=`. Note this touches
   `_certification.py`, which the regenerative add-on also needs — do it once, for both.
4. **L3 — brand strings.** Sweep the 9 templates and `PAGES` onto the identity block. Keep
   `test_the_refusal_is_the_d17_wording` green by asserting the *default* value.
5. **Branch rehearsal — the acceptance test (§10).** Seed a fictional second group in a scratch
   settings file, run `verify.sh`, and prove the diff is empty.
6. **Separately, as its own PRD:** SAOSO Section A + C ingestion (D41 gap, one migration).
7. **Separately, data only:** ingest the three branch-setup documents (§6).

Steps 1–5 are the branch-readiness work. Step 6 is the only migration and must not be bundled.

## 10. Acceptance test — the branch-readiness proof

> **A second branch deployment requires: a new `.env`, a new deployment identity block, a new
> seed run, and — only if it brings its own procedures document — one new
> `knowledge/sections/<scheme>.py`. `git diff` over `core/` and `knowledge/models.py` is
> empty.**

That is §4.8's retarget checklist, pointed at a *branch* instead of a standard, and it is the
only honest way to claim "usable by all SAOSA branches". Until it is demonstrated, the claim is
an argument, not a fact.

## 11. Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | **The acceptance test is claimed from inspection, not from a rehearsal.** This document's §2–§4 is evidence; §10 is a promise | Step 5 must actually run, with the diff pasted into the PRD. Compare `product/docs/context/testing_hazards.md` §1.6 — a guard nobody watched fail is not a guard |
| 2 | **~15 test files assert Outeniqua literals**, so a fork inherits 461 tests that disagree with its own content | Prefer asserting against the seed/identity block. Accept that a fork edits tests; do not let test literals dictate code structure |
| 3 | **A branch's OPP numbering will not match `knowledge/sections/opp.py`, and ingestion will silently produce zero sections** | `ingest_standard` must fail loudly on zero parsed sections per document — verify this before a branch attempts it |
| 4 | **Someone builds shape (ii) "just for the admin view"** | §IX is explicit. A tenant key appearing on any model is the signal to stop and re-read this document |
| 5 | **The FIELD workbook/form is treated as Outeniqua content** because they digitised it | §2: it is the PGS SA form, `6.` in a numbered national set. Naming it "our form" invites divergence, and divergence from a national form is a compliance problem, not a branding one |
| 6 | **Claim discipline is scoped to this deployment's strings** (`FORBIDDEN` in `test_claim_discipline.py:72`) | A branch's seals arrive via L2 with `issuer`; the forbidden-terms list must remain a *content* rule, and a national logo must not be publishable without an approval record |

## 12. What this document does not decide

- Whether shape (iii) is built.
- Whether SAOSA ever wants to see cross-branch data (it would need shape ii, and a POPIA
  assessment first).
- The add-on architecture — see `REGENERATIVE_ADDON_ARCHITECTURE.md`.
