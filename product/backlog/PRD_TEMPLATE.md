# PRD: [Feature Name]
**Status:** Refinement / Ready / In Progress
**Owner:** [Name / Role]
**Last Updated:** YYYY-MM-DD
**Scope:** [What is and isn't included]
**Reference:** [Related PRDs / docs / files]

---

## 1. Problem Statement
[What problem does this solve? Why now?]

## 2. Strategic Goal
[One-line goal. What does success look like?]

## 3. Proposed Solution
[High-level approach. Architectural decisions. Trade-offs.]

## 4. Technical Requirements
[Specific implementation requirements, API changes, data model changes.]

## 5. Execution Steps
1. ...
2. ...
3. ...

## 6. Success Criteria
- [ ] ...
- [ ] ...
- [ ] ...

## 7. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| ... | ... |

---

## Pre-Flight Checklist
- [ ] Models added to `core/models.py` or new app?
- [ ] Views added to correct `core/views/_<domain>.py`?
- [ ] Forms added to correct `core/forms/_<domain>.py`?
- [ ] Services added to correct `core/services/_<domain>.py`?
- [ ] URLs added to `core/urls.py` in the correct section?
- [ ] Tests added to `core/tests/test_<domain>.py`?
- [ ] Migrations generated and backwards-compatible?
- [ ] `select_related` / `prefetch_related` used in new queries?
- [ ] `transaction.atomic()` used for multi-table writes?
- [ ] No logic in templates (use template tags or model properties)?
