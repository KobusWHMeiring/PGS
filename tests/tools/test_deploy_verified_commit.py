"""The deploy installs the commit the gate verified — not origin's tip at pull time.

Step 1/8 fetches `origin/main` and archives **that commit** into a scratch tree, which is
the whole reason the gate means anything: "what is tested is exactly what the pull below
installs". Step 2/8 then used to run `git pull --ff-only origin main`, which fetches
*again*. Anything pushed during the gate — measured at 82 s on the VPS, and 126-223 s
cold on the dev box — is therefore installed without ever being tested, and step 8/8
still prints the sha that *was* verified.

Measured on the VPS 2026-11-03, and the reason these guards exist:

    ==> 1/8  Verifying origin/main     ->  7b2242343192b6fcbebfe48cd9a6a82d91b64492
    ==> 2/8  Pulling origin/main       ->  7b22423..06bb11a  main -> origin/main
    ✅ Deploy complete — 7b2242343192b6... is live

The tree was `06bb11a`; the log said `7b22423`. The delta that time was one HTML file in
`product/design/`, so nothing broke — and that is exactly why it would have gone unnoticed
next time, when the delta is a migration.

The fix is structural rather than a warning: fast-forward to `$VERIFY_COMMIT`, which step
1/8 already fetched, so the tested object *is* the installed object. If origin has moved
on, the next deploy verifies and installs it — the safe direction, and no window.

`test_the_shift_is_a_fast_forward` is the load-bearing one: `--ff-only` means a checkout
with local commits fails the deploy instead of silently merging unverified work.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY = REPO_ROOT / "deploy" / "deploy.sh"


def read() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def test_the_verified_commit_is_the_one_installed():
    assert 'merge --ff-only --quiet "$VERIFY_COMMIT"' in read()


def test_the_deploy_never_pulls_the_moving_remote_tip():
    """The exact shape of the defect: a second fetch after the gate has already run."""
    assert 'pull --ff-only origin "$GIT_BRANCH"' not in read()


def test_the_shift_happens_after_verification_and_before_the_backup():
    """Ordering is the argument: verified, then installed, then backed up, then migrated."""
    text = read()
    verified = text.index("==> 1/8  Verifying")
    shifted = text.index("merge --ff-only --quiet")
    backed_up = text.index("==> 3/8  Backing up")
    migrated = text.index("migrate --noinput")
    assert verified < shifted < backed_up < migrated


def test_head_is_asserted_before_anything_is_migrated():
    """So a later edit that moves HEAD cannot ship untested code behind a verified sha."""
    text = read()
    assert 'if [[ "$HEAD_NOW" != "$VERIFY_COMMIT" ]]' in text
    assert text.index("HEAD_NOW") < text.index("migrate --noinput")


def test_a_failed_fast_forward_aborts_instead_of_merging():
    assert "cannot fast-forward to the verified commit" in read()


def test_the_live_message_names_the_commit_that_was_verified():
    """The message is only trustworthy because the tree is asserted to be that commit."""
    assert '"$VERIFY_COMMIT is live"' in read()
