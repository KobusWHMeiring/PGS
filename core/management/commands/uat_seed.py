"""`manage.py uat_seed` — prepare and check the instance a UAT reviewer is about to judge.

Thin command, per `build_principles.md` §II: every rule lives in
`core/services/_uat.py`.

**Slice 1 is check-only, by design.** MVP 0's UAT needs no rows — its data is the seeded
corpus and the eight published documents — so a `--scenario` seeder would be a command
with nothing to create. The seeding half lands with MVP 1a, whose scenarios need an
applicant, a farm, a visit in `DRAFT` and a roster, and it will refuse to write unless
`UAT_ALLOW_SEED=1` and the database is not the production one (PRD §4.4, decision D1).

    python manage.py uat_seed --check
    python manage.py uat_seed --check --expect-chunks 366 > preflight.txt
    python scripts/uat_runner.py --file tests/uat/… --preflight preflight.txt

`--check` exits non-zero when a **blocking** row fails. Advisory rows (the health probe,
`pdftotext`) are printed and do not fail the exit code — a dev box without a Celery worker
is a normal place to read this output, and failing it would teach the operator to ignore
the command.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from core.services._uat import EXPECTED_CHUNKS, preflight


class Command(BaseCommand):
    help = "Check (never seed, for MVP 0) the state a UAT reviewer needs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Print observed vs expected for every preflight row (the only mode in MVP 0).",
        )
        parser.add_argument(
            "--expect-chunks",
            type=int,
            default=EXPECTED_CHUNKS,
            help=f"The corpus size this instance should hold (default {EXPECTED_CHUNKS}).",
        )

    def handle(self, *args, **options):
        if not options["check"]:
            # A bare invocation must not look like it did the right thing.
            self.stderr.write(
                "nothing to do: MVP 0 needs no seeded rows, so only --check exists. "
                "The per-scenario seeder lands with MVP 1a."
            )
            raise SystemExit(2)

        report = preflight(options["expect_chunks"])

        width = max(len(row.name) for row in report.rows)
        for row in report.rows:
            marker = "ok  " if row.ok else ("FAIL" if row.blocking else "warn")
            self.stdout.write(f"[{marker}] {row.name.ljust(width)}  {row.observed}")
            self.stdout.write(f"{' ' * 7}{row.command}")
            self.stdout.write(f"{' ' * 7}expected: {row.expected}")
            if row.note:
                self.stdout.write(f"{' ' * 7}note: {row.note}")

        self.stdout.write("")
        if report.is_ready:
            self.stdout.write(
                self.style.SUCCESS(f"preflight: ready - {len(report.rows)} checks, no blocking failure")
            )
            return

        self.stdout.write(
            self.style.ERROR(
                "preflight: NOT ready - "
                + ", ".join(row.name for row in report.blocking_failures)
            )
        )
        raise SystemExit(1)
