# PRD: UAT sign-off tooling — an HTML judgement surface with the data already loaded

**Status:** **Slice 1 BUILT 2026-10-22** — moved to `In Progress/`. 768 tests green, artefact driven
in a real browser, export round-tripped through `uat_signoff.py`. **UAT unsigned**: nothing is
*signed* until a person has judged and `uat_signoff.py` has written the results in. Slices 2 and 3
(the `uat-setup` format + command lint, and the 1a seeds) are not built.
**Decisions D1–D4 are settled** (§9) — recorded rather than absorbed, on the defaults the product
owner confirmed on 2026-10-22.
**Owner:** Product (sign-off), Build (tooling)
**MVP:** MVP 0 acceptance, reused for MVP 1a and every slice after it
**Scope:** How a human reviewer gets a scenario's data, runs it, judges it, and signs. **Not** in
scope: changing what UAT may contain (that is `writing-uat-tests`), and not a test runner.
**Reference:** `tests/uat/mvp0_standards_and_public_site_uat.md`;
`tests/uat/mvp1a_in_office_visit_uat.md`; the `writing-uat-tests` skill's hard gate;
`product/docs/context/build_principles.md` §VIII; HANDOVER §3 (UAT sign-off seats).

---

## 1. Problem

**Nothing in `tests/uat/` is signed.** By the local backlog rule an unsigned UAT makes a
human-judged item *partial*, so C1 (public site) and D (chatbot) are partial today and MVP 0 cannot
close. The blocker is not the scenarios — they are written, specific, and each carries a
`Judgement:` clause. The blocker is that signing one takes a developer.

Four concrete reasons, all measured in the current files:

| # | Problem | Evidence |
|---|---|---|
| 1 | **Setup is prose, not commands.** | Scenario 1 says *"Corpus seeded (pre-test setup complete)"*; the actual commands live in `HANDOVER.md` §8, in four documents, and changed in D52/D53 |
| 2 | **The commands in the file can be wrong and nobody notices.** | `mvp1a` pre-setup says `manage.py load_template core/templates_data/crops.v1.json` — **no such command exists** (1a is not built). A reviewer would hit an error and stop |
| 3 | **The reviewer has no way to record what they saw.** | There is a `## Sign-off` table with four role rows and no place for a result per scenario, a note, or evidence |
| 4 | **The signature drifts from the file.** | Signing means hand-editing markdown; nothing checks that a scenario marked PASS still reads the same |

It has become urgent because **the app is deployed**. The people who must sign are the PGS
administrator, a committee reviewer and a consumer member — not shell users — and until now the only
way to prepare their data was to be the person who wrote `HANDOVER.md`.

## 2. Goal

A reviewer with no shell confidence can, in one sitting per file:

1. see whether the instance is ready (with the expected values), and be told exactly what to run if
   it is not;
2. read each scenario's `Judgement:` question (verbatim — it is the whole point of the item);
3. run the scenario in the app, with any data it needs already created;
4. record PASS / FAIL / N-A **with a reason and a note**, and their name and date;
5. hand back an artefact that writes the results into the UAT markdown, so *signed* becomes a fact
   the backlog can read.

## 3. What this is not

The `writing-uat-tests` skill's hard gate governs this PRD, and the tooling must not weaken it:

- **It is a judgement surface, not a test runner.** The runner never decides PASS/FAIL. It shows the
  `Judgement:` clause and waits for a person.
- **`setup` prepares; it never decides.** A setup command may seed or check; the result of a command
  is never the verdict.
- **It must not present the automated items.** Both UAT files carry an *"Automated coverage (NOT
  UAT)"* table. Rendering those rows as checklist items is the exact failure the skill exists to
  prevent, so the generator must exclude them and a test must assert they are absent.

## 4. Proposed solution

Four pieces. The first three are small and independent; the fourth is where the real design risk is.

### 4.1 The skill — `.agents/skills/pgs-presenting-uat/SKILL.md`

A **local** skill (naming follows `pgs-reading-the-backlog`), triggered by *"present the UAT"*,
*"get the UAT signed"*, *"prepare the sign-off for <feature>"*. It:

1. parses one `tests/uat/<slug>.md`;
2. refuses if any scenario lacks a `Judgement:` clause (the gate, enforced in code);
3. emits a single self-contained HTML file at `product/design/uat/<slug>.html`;
4. prints the preflight commands and their expected values for the operator to run first.

It does **not** edit the UAT file itself — that is the write-back script, so the skill stays
text-in / text-out like `pgs-writing-explorations`.

### 4.2 The runner — `scripts/uat_runner.py` → one HTML file

Zero build pipeline (repo rule): hand-written HTML + CSS + vanilla JS in one file, **no CDN, no
fonts, no network**, opens from `file://`. The design follows `product/design/DESIGN.md` tokens so it
looks like the product, and reuses the cream/Lora/Mulish palette rather than inventing one.

Per scenario:

```
Scenario 1 — Does the chatbot answer from the standard, or from general knowledge?
[ Category: grounding ]                                  [ PASS ] [ FAIL ] [ N-A ]

Judgement (the question you are answering)
  Does the answer read as a quotation of the standard rather than a plausible-sounding
  summary of general poultry knowledge? …

Setup — run these first (copy)
  $ python manage.py seed_deployment
  $ python manage.py publish_documents
  ✓ expected: 8 PublicDocument rows, media files present

Steps
  1. Ask: "What does the standard say about the minimum rest period for laying hens…"
  2. Read the answer and its citations.

Expected
  An answer with one or more citations naming a document and a section reference.

Your note (optional)            [                                     ]
Reviewer / role / date          [ name            ] [ role ▾ ] [ date ]
```

File-level header: feature, plan, PRD, generated-on, **environment** (see §7), the database the
commands will hit, and a **Preflight** panel of commands + expected values + the current observed
value where the runner can show it (it cannot query the DB from `file://`, so preflight values are
typed in by the operator or produced by `manage.py uat_seed --check` and pasted).

Behaviour that matters:

- **Autosave** to `localStorage` per file + scenario, so a reviewer can stop and resume.
- **N-A requires a reason** (Scenario 5 is N/A by D44, and the reason must survive).
- **Result is mandatory before export** — no silent blanks.
- **No data leaves the machine**: no fetch, no analytics, no remote fonts. A test asserts the HTML
  contains no `http://`, `https://`, `<script src` or `<link href` to anything but a local file.
- **Evidence**: a screenshot can be dropped onto the scenario and is embedded as a data URL *in the
  export only*. Default is note-only (decision D2 below).

### 4.3 The write-back — `scripts/uat_signoff.py`

```
python scripts/uat_signoff.py --file tests/uat/mvp0_standards_and_public_site_uat.md \
                              --from ~/Downloads/uat-mvp0-signoff.json [--dry-run]
```

It rewrites exactly two things and nothing else:

1. each scenario gains a `**Result:**` line (`PASS` / `FAIL — reason` / `N/A — reason`) plus the
   reviewer and date, immediately after its `Judgement:` paragraph;
2. the `## Sign-off` table gains a row per scenario (or one row per reviewer with the scenario list,
   D3).

`--dry-run` prints the diff. The test is a round-trip: apply an export, and the diff touches only
those lines; re-apply, and the diff is empty (idempotent). The UAT file stays the source of truth,
so the backlog rule keeps working unchanged.

### 4.4 The data layer — `manage.py uat_seed` and the preflight

Two halves:

**Preflight (`--check`, read-only).** Prints observed vs expected for the instance:

| Check | Command | Expected today |
|---|---|---|
| Settings and app | `manage.py check` | `System check identified no issues` |
| Dependencies | `curl -s localhost:8000/health/` | `db`, `redis`, `celery_broker`, `celery_worker` all `ok` |
| Corpus present | `DocumentChunk.objects.count()` | **366** (321 SAOSO + 30 OPP + 9 BPP + 8 landscape, after D52; 368 before) |
| Corpus embedded | `search()` reports `lexical_only` | `False` |
| Documents published | `PublicDocument.objects.filter(is_published=True).count()` | **8** |
| Extraction tool | `pdftotext -v` | the same implementation the fixtures pin (see risk 4) |

**Seed per scenario (`--scenario <slug>`, idempotent).** MVP 0 needs **no new rows** — its data is
the seeded corpus and the published documents. The command earns its place with 1a, whose scenarios
need an applicant, a farm, a visit in `DRAFT`, a questionnaire template and an input register. Its
contract:

- one scenario = the minimum state that scenario needs, created idempotently (keyed on a stable slug);
- it prints the URL and the exact values to use (farm name, applicant, visit date);
- `--check` and `--scenario` are separate, so a reviewer can look before writing;
- **it refuses to write unless `UAT_ALLOW_SEED=1` is set, and it names the database it is about to
  write to** (decision D1 below — this is the one guard that must not be negotiable).

### 4.5 A format change to the UAT files (small, and it fixes problem 2)

Each scenario's `**Setup:**` prose stays for the human, and gains a machine-readable block:

```markdown
**Setup:** Corpus seeded and eight documents published. Open `/ask/`.

```uat-setup
python manage.py seed_deployment
python manage.py publish_documents
# expect: 8 published documents, 366 chunks
```
```

Two rules, both testable:

- The generator renders these blocks as copyable commands — this is the answer to *"the relevant
  management commands to get the data loaded"*, sourced from the scenario rather than from the
  handover.
- A lint asserts every `manage.py <command>` named in a `uat-setup` block **exists** in
  `*/management/commands/`. That single check would have caught `load_template`, which has been in
  `mvp1a` since it was written.

## 5. Why this is worth building rather than hand-signing once

| | Hand-signing today | With the tooling |
|---|---|---|
| Prepare data | read HANDOVER §8, four commands, two of them changed by D52/D53 | one preflight block, one copy button, expected values shown |
| Know the instance is ready | trust | observed vs expected, with the chunk count spelled out |
| Record the judgement | none — the scenario has no result field | PASS/FAIL/N-A + reason + note, per scenario |
| Evidence | none | optional screenshot/notes in the export |
| Write the signature | hand-edit a table | `uat_signoff.py`, deterministic, diff-reviewable |
| Re-run next slice | start again from the handover | regenerate; only 1a needs new seeds |

The UAT files are reused for every slice. A one-hour tool per file, used by three seats on two files
now and every file after, is cheaper than a developer sitting in on each session.

## 6. Acceptance criteria

> **Correction (2026-10-22, at build time).** Criterion 1 said *"nine applicable scenarios"*. The
> file holds **ten scenarios, nine of them applicable** (Scenario 5 is N/A by D44). The artefact
> renders **all ten** — the N/A one included, carrying its D44 reason — because a scenario that
> disappears is indistinguishable from one nobody judged. The tests pin `10 / 9 / 1`.
>
> **Criterion 9 belongs to slice 3.** Slice 1 is check-only: MVP 0's UAT needs no new rows, so a
> `--scenario` seeder would have nothing to create, and `uat_seed` refuses a bare invocation rather
> than pretending. The `UAT_ALLOW_SEED=1` guard lands with 1a's seeds and is untested until then.

**Status: 1–8 built and asserted; 9 deferred with slice 3.**

1. `python scripts/uat_runner.py --file tests/uat/mvp0_standards_and_public_site_uat.md` produces one
   HTML file that opens from `file://` with the network disabled and renders all **ten** scenarios —
   nine applicable, and Scenario 5 as N/A with its D44 reason.
2. The HTML contains every scenario's `Judgement:` text verbatim, and **none** of the rows from the
   *"Automated coverage (NOT UAT)"* table (asserted by test).
3. The HTML contains no `http://`, `https://`, `src=` or `href=` that is not a local file (asserted).
4. A scenario with no `Judgement:` clause makes the generator **exit non-zero** and name the scenario
   (asserted with a fixture UAT file).
5. Every `manage.py` command in every `uat-setup` block exists (lint, asserted against
   `*/management/commands/`), and the lint fails on the current `load_template` reference once that
   block is added to `mvp1a`.
6. `uat_signoff.py --dry-run` prints a diff; without `--dry-run` the diff touches only scenario
   `**Result:**` lines and the `## Sign-off` table; a second application changes nothing.
7. A result cannot be exported unless the reviewer name and date are filled, and N/A requires a
   reason (a JS guard plus a check in `uat_signoff.py`).
8. `manage.py uat_seed --check` prints observed vs expected for the six preflight rows above, and
   exits non-zero when the corpus count is wrong.
9. `manage.py uat_seed --scenario <slug>` without `UAT_ALLOW_SEED=1` refuses and names the database.
   — **slice 3 only** (see the correction above).

## 7. Where does UAT run? (decision D1 — blocking)

This is the decision that changes the shape of everything else, and it changed when the app was
deployed.

| Option | What it means | Cost | Risk |
|---|---|---|---|
| **A. Against production** | Sign-off on the live site with real data | cheapest for the reviewer | seeding demo rows onto production is not acceptable; chat scenarios consume the live rate limit and API quota; a wrong click is visible to the public |
| **B. Against a staging copy** | A second instance (or the same box, second DB + `StandardSet`) with a copy of production data | one more deploy target; the "is it the deployed build?" question must be answered by a commit sha check | the reviewer signs a build that is not what ships, unless the sha is checked |
| **C. Local** | Sign-off on the dev box | zero infra | the deployed environment (poppler vs Xpdf, TLS, nginx, the real phone over the network) is exactly what some scenarios judge |

**Recommendation: B for write scenarios, A for read-only ones, and C is not acceptable for C1/D.**
Scenario 6 (*"is the chat usable on a real phone?"*) is about the deployed site over a real network;
Scenario 10 is about answer wording. Neither needs demo rows. It is the **1a** scenarios that need a
farm, a visit and a roster — those should never touch production, so `uat_seed` writes only where
`UAT_ALLOW_SEED=1` and the database name is not the production one.

Whatever is chosen, the runner's header must print the **commit sha and the database name** the
reviewer is signing, and the export must carry them. Otherwise "signed" means "signed something".

## 8. Risks

| Risk | Mitigation |
|---|---|
| The HTML looks like a test harness and reviewers start trusting its checks | No PASS/FAIL logic beyond the reviewer's own choice; the `Judgement:` clause is the largest text on the card; §3 is quoted in the skill |
| Seeding demo data on production | `UAT_ALLOW_SEED=1` + database name printed; D1 resolves where it may run at all |
| Setup commands drift from reality | The existence lint (§4.5) fails the build when a command is renamed or absent |
| The export is lost / the reviewer's browser clears storage | Autosave, plus a "Download sign-off" button that always works; the note fields are plain text |
| Base64 screenshots bloat the repo | Decision D2; default is note-only, images live in the export JSON, not in git |
| Sign-off says PASS on a build that is not the deployed one | Header and export carry the commit sha and database name; a test asserts the field is present |
| The tool becomes a way to mark things PASS without running them | `uat_signoff.py` refuses a PASS with no note for scenarios whose `Judgement:` names a physical/device step; the seats in §Sign-off remain human |

## 9. Open decisions for the product owner — **SETTLED 2026-10-22**

All four confirmed by the product owner on 2026-10-22, on the defaults below. They are recorded
here because they are product decisions, not implementation details, and because each one is
visible in the artefact:

| # | Decision | Options | **Decided** | Where it shows |
|---|---|---|---|---|
| **D1** | Where does UAT run? | A production / B staging / C local / A+B split | **B for write, A for read-only.** The runner header and the export carry the commit sha, the working-tree state and the database name; `uat_seed` will refuse without `UAT_ALLOW_SEED=1` when slice 3 lands | `<header class="meta">`, `export.environment` |
| **D2** | Is a screenshot required for a PASS? | required / optional / not supported | **Optional, note-only by default.** The page accepts an image and embeds it in the export only; no guard requires one, and nothing is uploaded | the Evidence field on every card |
| **D3** | One sign-off row per scenario, or per reviewer? | per scenario / per reviewer with a scenario list | **Per scenario** — it is what the backlog needs in order to flip a scenario to signed. The four role rows in `## Sign-off` stay for the seats | `### Per-scenario results` in the UAT file |
| **D4** | Who may sign, and may one person sign two roles? | one seat each / product may co-sign | **One seat each, product may co-sign.** Each card carries its own reviewer and role, so one file judged by two people produces two seats | the Role select on each card |

## 10. Slices

| Slice | Delivers | Unblocks |
|---|---|---|
| **1 — MVP 0 sign-off** | `uat_runner.py` + `pgs-presenting-uat` skill + `uat_signoff.py` + preflight, for `mvp0_standards_and_public_site` only. **No `uat_seed`** — MVP 0 needs no new rows | the six unsigned scenarios (1, 2, 3, 6, 9, 10) and C1's (4, 6, 8) — i.e. C1 and D move from *partial* to *done* |
| **2 — the setup block + lint** | the `uat-setup` format and the command-existence lint, retro-fitted to both UAT files | problem 2; the `load_template` gap becomes visible before 1a ships |
| **3 — 1a seeds** | `uat_seed --scenario` for the twelve 1a scenarios | the 1a UAT, once 1a is built and the `0∥` spike has frozen the visit pack |

**Slice 1 is the whole of the immediate need** and should be reviewed by the same three seats that
must sign. Slices 2 and 3 land with MVP 1a.

---

## Pre-Flight Checklist

- [x] Models changed? **No** — no migration.
- [x] Services in the correct module? `scripts/` (developer tooling) + a management command; no
      `knowledge`→`core` import.
- [x] Views touched? **No** — nothing in the product serves the runner; it is a file opened from disk.
- [x] Tests to add? `scripts/uat_runner.py` and `uat_signoff.py` get tests in `tests/tools/` (a new
      directory, since they are not app code), the command-existence lint runs in the gate.
- [x] `select_related` / `prefetch_related`? Only the `uat_seed --check` counts, which are single
      aggregate queries.
- [x] `transaction.atomic()` for multi-table writes? `uat_seed` creates a farm + visit + roster; it
      writes inside one transaction and is idempotent on a slug.
- [x] No logic in templates. No new runtime dependency. No CDN.

---

## Built 2026-10-22 — what landed, and the two defects only running it found

**Slice 1 is built, and nothing is signed.** Signing is a human act; what exists is the surface that
makes it possible without a developer in the room.

| Piece | File | Note |
|---|---|---|
| Format, the `Judgement:` gate, the applicability scan | `scripts/uat_parse.py` | Pure, no Django. The only code that knows the UAT file's shape |
| The artefact shell (CSS, script, markdown renderer, environment) | `scripts/uat_page.py` | Split out of the runner when it crossed the 30 KB cap |
| The runner | `scripts/uat_runner.py` | Assembles the page; refuses a broken or stale UAT |
| The write-back | `scripts/uat_signoff.py` | `--dry-run` diff; idempotent; refuses a malformed export |
| The preflight | `core/services/_uat.py` + `manage.py uat_seed --check` | Read-only; six rows; blocking vs advisory |
| The skill | `.agents/skills/pgs-presenting-uat/SKILL.md` | The three moves and the hard rules |
| Tests (gate) | `tests/tools/` (63) | In `pytest.ini` `testpaths`, or they would never run in the gate |
| Tests (browser) | `tests/e2e/test_uat_artefact.py` (4) | Outside the gate, and the only check that executes the page's script |

### The applicability scan, in one paragraph

An N/A outlives the decision that caused it unless something checks. `scan_applicability()` requires
every N/A scenario to cite a `D<n>` in its `**Status:**` line, requires that id to exist in
`PGS_PLATFORM_SPEC.md` §18.3, and requires that decision's resolution to *still* read as a deferral
(`deferred`, `out of MVP`, `withheld`, `post-MVP`, …). If D44 is ever edited to say C3 is picked up,
the runner exits non-zero and names Scenario 5 instead of quietly printing a greyed-out card for a
scenario that has become deliverable. The count is pinned by test (`10 scenarios / 9 applicable /
1 N/A`) so a scenario cannot flip to N/A unseen. **No model decides this** — see the skill's rule 7:
a signature has to be reproducible from the commit.

### Two defects, both invisible to a green test suite

1. **The artefact's script did not parse.** Extracting the JS into `uat_page.py` left the original
   IIFE's closing `})();` in the script body *and* wrapped it again, so Chromium threw
   `Unexpected token '}'`. Every structural assertion stayed green — the cards, the judgements and
   the payload are all server-rendered, and a greps-based test cannot execute a script. Found only by
   loading the page in Playwright and reading a console error. `tests/e2e/test_uat_artefact.py`
   now pins it: with the defect re-introduced, all 63 gate tests stay green and three of the four
   browser tests go red.
2. **`write_text` emits CRLF on Windows**, so the artefact differed per platform and every
   regeneration was a whole-file diff. This is `testing_hazards.md` §1.27, already recorded; the
   runner passes `newline="\n"` and a test asserts no `\r\n` and byte-identical output on a second
   run.

### Slice 1.5 — the console, added 2026-10-22 at the product owner's request

The request was *"wire the management commands up as buttons so I don't have to copy and
paste"*. A `file://` artefact cannot run `manage.py`, and giving it a network call would
destroy the property the whole design rests on (§4.2, AC 3). So the buttons live on a
**second, served page**: `/uat/`, staff-only (`staff_member_required` → admin login), POST +
CSRF, and it can only run keys that are in `core/services/_uat_console.ACTIONS`.

| Button | Runs | Writes |
|---|---|---|
| Re-check the instance | the six preflight rows | no |
| Publish the documents | `publish_documents` (idempotent on sha256) | yes |
| Seed the deployment | `seed_deployment` (idempotent) | yes |
| Rebuild the UAT page | `scripts/uat_runner.py` **as a subprocess**, with the live preflight | yes |

**Shown, never clickable:** `ingest_standard --force` (deletes and re-embeds: API cost,
minutes, and every historical `ChatMessage` detaches from its evidence) and
`uat_signoff.py` (needs the reviewer's downloaded file). A button for either would be a
button that deletes the corpus or cannot work. `test_no_destructive_command_is_reachable`
asserts `--force` is not in `ACTIONS` and cannot be posted.

The console prints the **same preflight text** as `manage.py uat_seed --check` and the
artefact, from one `render_preflight()`, so the three cannot disagree about an instance.
Verified in a browser: staff login, six rows observed vs expected, `Re-check` returning
`done 1206 ms` with its own output, no console errors, and the artefact still containing
zero `http://`, `https://`, `src=` or `href=`.

### Also fixed in the same session: the cache and the escalation reason

Bringing the UAT up made the flagship Scenario 1 question refuse, reproducibly. Two defects,
both in `answer_question`:

1. **The reply was cached before it was audited**, so a reply the citation audit rejected was
   re-served for the whole TTL — one bad generation became a refusal that reproduced exactly.
   The write now happens only after every refusal branch, so **only an accepted answer is
   cached** (a refusal is never cached, which costs one model call on a repeat and is the
   right trade).
2. **An audit rejection was recorded as `NO_CITATIONS`**, hiding a model-contract violation
   behind a reason that reads as a thin corpus. It is now its own reason, `CITATION_AUDIT`
   (**D54**), and the model returning zero citations still records `NO_CITATIONS`.

Five tests pin it, and reintroducing the old ordering fails two of them. See
`testing_hazards.md` §1.31 for the evidence.

### Still open

* **Slice 2** — the `uat-setup` format and the `manage.py <command>` existence lint. Worth starting
  with, because it is what catches `load_template` in `mvp1a` (problem 2 §1), and the lint is ~20
  lines against `*/management/commands/`.
* **Slice 3** — `uat_seed --scenario` for the twelve 1a scenarios, behind `UAT_ALLOW_SEED=1`.
* **The reviewer's evidence is optional** (D2), so a PASS can carry no artefact at all. The guard
  that `uat_signoff.py` refuses a PASS with no note for device scenarios is still not built; it needs
  a way to mark a scenario as device-dependent in the file rather than guessing from its prose.
* **`Generated 2026-10-20`** in the shipped artefact is the dev box's clock, not a typo: the artefact
  records `date.today()` on the machine that generated it, which is the correct behaviour and a
  reason to regenerate it on the box whose commit it claims.
