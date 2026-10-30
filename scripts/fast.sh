#!/usr/bin/env bash
#
# fast.sh — the inner loop. "Did I just break something?"
#
# NOT the gate. `scripts/verify.sh` answers "is this tree shippable?" and is run once per
# commit; this answers the smaller question after every edit and must stay under ~20s warm.
#
# What it does differently from the gate, and why:
#
#   -m "not slow"   `slow` is a *measured* marker (see pytest.ini): tests over ~0.5s, tests
#                   that spawn a process, tests that drive a browser. They are where 60%+ of
#                   the suite's time goes and they are the ones a one-line edit rarely breaks.
#   --reuse-db      the schema is not the edit. Rebuilding it costs ~1.2s here, plus a stale
#                   `test_` database can wedge the run (testing_hazards.md §3).
#   -x --ff         stop at the first failure, and run whatever failed last time first.
#
# Three budgets, one script — pick by what you are doing, not by mood:
#
#   ./scripts/fast.sh --critical    ~20 s warm / ~55 s cold
#                                        the non-negotiables only (CRITICAL_TESTS below)
#   ./scripts/fast.sh               ~2.5 m   the whole suite minus `slow` — "did I break something?"
#   ./scripts/verify.sh             ~3.5 m   the gate — "is this tree shippable?" (cold figures;
#                                            warm is much less, and a first run of a session pays
#                                            the cache penalty — TESTING_TIME_PLAN.md §1)
#
# `--critical` is a **subset of files the gate already runs**. It is not a second suite: no test
# lives only here, and nothing was removed from the gate to make it fit. A lane that exists
# outside the gate drifts, and it drifts silently (testing_hazards.md §3.11) — so the answer to
# "this is too slow" is always to move a file *between* these budgets, never to invent a fourth.
#
# The full lane is `./scripts/verify.sh`. A change that only ever passes `--critical` has not
# been gated — in particular `tests/e2e` (deliberately outside both) and anything marked
# `slow`. Run `pytest -m slow` when you touch a template, an extraction, or a management
# command.
#
# Usage:
#   ./scripts/fast.sh                    # the lane
#   ./scripts/fast.sh --critical         # the under-a-minute set
#   ./scripts/fast.sh core/tests/test_x.py -vv
#
set -euo pipefail

# The tests that guard what this repo cannot get wrong, each for a stated reason:
#
#   test_claim_discipline      the public surface may not invent a certification claim
#   test_architecture          knowledge never imports core (the library boundary)
#   test_chatbot_guardrails    a citation that cannot be checked refuses the answer
#   test_chatbot_grounding     the answer is grounded in retrieved passages, not memory
#   test_retrieval_scope       the corpus boundary is applied before ranking (D16)
#   knowledge/test_retrieval   the retrieval floors that pin search_terms' behaviour
#   test_eval_retrieval        the retrieval instrument cannot lie about what it measured
#   test_test_harness          the fast hasher cannot reach manage.py, WSGI or the gate
#
# The list is self-checking in one direction only: a renamed or deleted file is a pytest error
# (exit 4, "file or directory not found"), so the lane cannot silently shrink. It cannot tell you
# about a *new* invariant — when you add a guard for something this repo must not get wrong, add
# its file here in the same commit.
CRITICAL_TESTS=(
    core/tests/test_claim_discipline.py
    core/tests/test_architecture.py
    core/tests/test_chatbot_guardrails.py
    core/tests/test_chatbot_grounding.py
    core/tests/test_retrieval_scope.py
    knowledge/tests/test_retrieval.py
    tests/tools/test_eval_retrieval.py
    tests/tools/test_test_harness.py
)

if [ "${1:-}" = "--critical" ]; then
    shift
    set -- "${CRITICAL_TESTS[@]}" "$@"
fi

if [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python"
fi

# The same two preconditions the gate checks. A loop that dies on a missing key teaches
# people to stop using the loop.
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    echo "ERROR: DJANGO_SECRET_KEY is not set. See scripts/verify.sh." >&2
    exit 2
fi
export DATABASE_URL="${DATABASE_URL:-postgres://pgs:pgs@localhost:5433/pgs_verify}"
# Point the extractor at a path that cannot exist: the parsers' goldens read committed page
# fixtures, and a live `pdftotext` makes the loop both slow and machine-dependent (§2.9).
export PDFTOTEXT_BIN="${PDFTOTEXT_BIN:-$PWD/scripts/_no_extractor}"

exec "$PYTHON" -m pytest -q -m "not slow" --reuse-db -x --ff "$@"
