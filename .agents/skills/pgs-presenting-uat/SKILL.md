---
name: pgs-presenting-uat
description: Use when asked to "present the UAT", "get the UAT signed", "prepare the sign-off for <feature>", or when a `tests/uat/<slug>.md` needs to become something a non-developer can judge, record and hand back. Produces a self-contained HTML judgement surface plus the preflight the reviewer must run first.
---

# Presenting a UAT

## Overview

A UAT file is written for a person, but its setup lives in a handover, its results have
nowhere to go, and signing it means hand-editing markdown. This skill turns one
`tests/uat/<slug>.md` into one HTML page a reviewer with no shell confidence can open
from disk, judge, and export — and then writes that export back into the markdown, so
*signed* becomes a fact the backlog can read.

It is **three moves**, and they are separate on purpose:

| Move | Script | What it produces |
|---|---|---|
| **Prepare** | `manage.py uat_seed --check` | observed vs expected for the instance |
| **Present** | `scripts/uat_runner.py` | `product/design/uat/<slug>.html` |
| **Close** | `scripts/uat_signoff.py` | `**Result:**` lines + the sign-off table, in the UAT file |

The skill is text-in / text-out like `pgs-writing-explorations`. It never edits the UAT
file itself — that is the write-back script, so there is exactly one path from an export
to the file.

## Hard rules

1. **It is a judgement surface, not a test runner.** The page shows each scenario's
   `Judgement:` clause and records the reviewer's call. Nothing in it scores, checks or
   decides. If you find yourself adding a condition that sets PASS, stop — that is an
   automated test that should not have been in the UAT at all.
2. **`setup` prepares; it never decides.** A command's output is never the verdict.
3. **Never present the "Automated coverage (NOT UAT)" table.** The runner excludes it by
   parsing only `## Scenario N — …` sections. A test asserts no automated row reaches the
   page. Rendering those rows is the exact failure `writing-uat-tests` exists to prevent.
4. **A scenario with no `Judgement:` clause is refused, not rendered.** The runner exits
   non-zero and names the scenario. Do not "helpfully" present it anyway.
5. **An N/A must cite the decision that caused it.** `scripts/uat_parse.py` cross-checks
   the cited `D<n>` against `PGS_PLATFORM_SPEC.md` §18.3 and refuses if the decision is
   gone or no longer reads as a deferral. An unexplained N/A looks like a failed check to
   the next reviewer, and an N/A whose reason expired is a scenario nobody re-judges.
6. **No network, ever.** The artefact must open on a laptop with the wifi off and make
   zero requests — no CDN, no font, no analytics. A test asserts the file contains no
   `http://`, `https://`, `src=` or `href=`.
7. **No model decides anything here.** Not applicability, not the result, not the wording
   of the reason. A signature has to be reproducible from the commit; an answer that
   changes when a provider updates its weights is not evidence. This is the same rule as
   HANDOVER §4's "do not add a classifier".
8. **Record what it was signed against.** The header and the export carry the commit and
   the database. "Signed something" is not a signature.

## The sequence

```bash
# 1. Prepare, and keep the output — the reviewer sees what the instance looked like.
python manage.py uat_seed --check > preflight.txt

# 2. Present. Runs the applicability scan; refuses a broken or stale UAT.
python scripts/uat_runner.py --file tests/uat/mvp0_standards_and_public_site_uat.md \
                             --preflight preflight.txt \
                             --database pgs_dev
#    -> product/design/uat/mvp0_standards_and_public_site.html

# 3. Hand the file to the reviewer. They judge every scenario and download
#    uat-<slug>-signoff.json. Nothing they do leaves their machine.

# 4. Close. Review the diff, then apply it.
python scripts/uat_signoff.py --file tests/uat/mvp0_standards_and_public_site_uat.md \
                              --from ~/Downloads/uat-mvp0_standards_and_public_site-signoff.json \
                              --dry-run
python scripts/uat_signoff.py --file tests/uat/mvp0_standards_and_public_site_uat.md \
                              --from ~/Downloads/uat-mvp0_standards_and_public_site-signoff.json
```

Then commit the UAT file. The signature lives in the repo, next to the scenarios it
judged, in the same commit as the code it accepted.

## What the reviewer sees

Per scenario: the `Judgement:` question in the largest block on the card (it is the whole
point of the item), then setup, steps, expected, and any recorded prior observation. Then
PASS / FAIL / N-A, a note, an optional screenshot, and their name, seat and date.

Behaviour that matters, and why:

- **Autosave** to `localStorage` per file and scenario — a session can be resumed.
- **FAIL and N/A require a reason.** An unexplained failure is not a finding; an
  unexplained N/A is indistinguishable from a skipped check.
- **Every scenario needs a result, a name and a date before export.** No silent blanks.
- **N/A scenarios arrive pre-filled with the decision's reason** (Scenario 5 with D44), so
  a reviewer new to the group can see *why* it is greyed out.
- **One seat per signature.** The product owner may co-sign (decision D4). The header panel
  fills details across cards; each card can still be overridden, because a file judged by
  a committee reviewer and a consumer member produces two seats.

## What to check before you say it is ready

- [ ] `python scripts/uat_runner.py …` exits 0 and names the applicable / N/A counts.
- [ ] Every scenario's `Judgement:` clause appears in the artefact (verbatim in the
      `uat-data` payload, rendered on the card).
- [ ] `grep -c "http://\|https://\|src=\|href=" product/design/uat/<slug>.html` is **0**.
- [ ] The artefact renders with JavaScript disabled (it is server-rendered; the script only
      adds state).
- [ ] Opening it in a browser with the network throttled to offline shows the whole page.
- [ ] `uat_signoff.py --dry-run` shows only `**Result:**` lines and the sign-off table in
      the diff.
- [ ] Running `uat_signoff.py` twice changes nothing the second time.
- [ ] `python -m pytest tests/e2e/test_uat_artefact.py -q` is green. **This is the only check
      that executes the page's script.** The artefact is server-rendered, so a script that does
      not parse leaves every structural test green and every button dead
      (`testing_hazards.md` §1.30 — it happened once).
- [ ] Every `manage.py` command in the output exists — this is the slice-2 lint
      (`uat-setup` blocks), and until it lands, read the preflight by eye.

## Anti-patterns

| Anti-pattern | Why it is wrong | Do instead |
|---|---|---|
| Rendering the automated-coverage table as checklist rows | Asks a human to confirm what pytest proves, and hides the real gap | The runner excludes it; the test pins that |
| Adding a "Run check" button that turns a row green | That is a test runner | Leave the judgement to the reviewer |
| Marking a scenario PASS by default | A signature nobody made | Blank until judged; the export refuses blanks |
| A hand-edited `**Result:**` line | It drifts from the file and is unreviewable | `uat_signoff.py`, so the diff is the review |
| "The reviewer said it was fine in chat" | Not a signature | The export JSON, applied to the file |
| Using a model to decide whether a scenario still applies | Irreproducible; the artefact stops being evidence | The decision-cite scan in `uat_parse.py` |

## Files

| Path | Role |
|---|---|
| `scripts/uat_parse.py` | Parses the UAT format; the `Judgement:` gate; the applicability scan |
| `scripts/uat_runner.py` | Renders the artefact, embeds the verbatim payload |
| `scripts/uat_signoff.py` | Validates the export, writes results back, idempotent |
| `core/services/_uat.py`, `core/management/commands/uat_seed.py` | The preflight |
| `tests/tools/test_uat_*.py` | The guarantees above, each mutation-tested |
| `tests/uat/<slug>.md` | Source of truth for the scenarios and, after sign-off, the results |
