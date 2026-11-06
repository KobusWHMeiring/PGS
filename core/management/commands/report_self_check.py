"""`report_self_check` — the aggregate, as a command rather than a page (§4.5).

Why this is not a view, in one sentence: a published figure about who is *not* applying is a public
claim about the group's own catchment, and DESIGN §1 says an unverified claim does not ship. Internal
first — a report for the group, for PGS South Africa and for SAOSO.

The threshold is not decoration. A catchment of a few dozen farms means a "cell" can be one person,
and a census cell with one person in it is that person. `--min-count` (default 5) is refused *below*
the threshold, and the refusal is printed rather than the cell being silently dropped: a reader must
be able to tell "no data" from "too little to say".

Bands are aggregated in SQL; the answer sets are counted in Python from `records_held`/`practices`,
because a JSON key is not a column and pretending otherwise with raw SQL would be a second query
language in a management command.
"""

from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Count

from core.models import SelfCheckDemographic, SelfCheckReport
from core.services._selfcheck import ANSWER_NO, ANSWER_PARTLY, ANSWER_RATHER_NOT_SAY, ANSWER_YES

RECORD_KEYS = ("B1", "B2", "B3", "B4", "B5", "B6", "B7")
PRACTICE_KEYS = ("C1", "C2", "C3", "C4", "C5")

BAND_COLUMNS = (
    ("hectares_band", "Total land"),
    ("pasture_band", "Pasture"),
    ("land_history_band", "Land history"),
    ("turnover_band", "Turnover band"),
)


class Command(BaseCommand):
    help = "Count what the public self-check collected. Totals only, and never below --min-count."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-count",
            type=int,
            default=5,
            help="The smallest cell this command will print (default 5). Below it, it says so.",
        )
        parser.add_argument(
            "--demographics",
            action="store_true",
            help="Include the census cells, each subject to --min-count.",
        )

    def handle(self, *args, **options):
        minimum = max(1, int(options["min_count"]))
        reports = SelfCheckReport.objects.all()
        total = reports.count()
        self.stdout.write(f"Self-check reports: {total}")
        if total == 0:
            self.stdout.write("Nothing to report yet — no visitor has consented to their answers.")
            return

        for column, label in BAND_COLUMNS:
            rows = (
                reports.exclude(**{f"{column}": ""})
                .values(column)
                .annotate(n=Count("id"))
                .order_by("-n", column)
            )
            self.stdout.write(f"\n{label}")
            if not rows:
                self.stdout.write("  (nobody answered)")
            for row in rows:
                self.stdout.write(f"  {row['n']:>4}  {row[column]}")

        held = [row or {} for row in reports.values_list("records_held", flat=True)]
        practices = [row or {} for row in reports.values_list("practices", flat=True)]
        self._uptake("Records a visit checks (of the answers given)", RECORD_KEYS, held)
        self._uptake("Practices", PRACTICE_KEYS, practices, known=("YES", "NO", "MIX", "SOME", "PLAN"))

        exits = Counter(row for row in reports.exclude(exit_reason="").values_list("exit_reason", flat=True))
        self.stdout.write("\nWhy not applying yet")
        if not exits:
            self.stdout.write("  (nobody said)")
        for reason, count in exits.most_common():
            self.stdout.write(f"  {count:>4}  {reason}")

        if options["demographics"]:
            self._demographics(minimum)

    def _uptake(self, title, keys, rows, known=None):
        self.stdout.write(f"\n{title}")
        for key in keys:
            counts = Counter(row.get(key) for row in rows if row.get(key))
            if known:
                # Practices have per-question answer sets; only the shared codes are summarised,
                # and the raw counts are printed so a new option cannot hide in a total.
                summary = ", ".join(
                    f"{code} {counts[code]}" for code in known if counts.get(code)
                ) or ", ".join(f"{code} {n}" for code, n in counts.most_common())
            else:
                summary = (
                    f"yes {counts[ANSWER_YES]}, partly {counts[ANSWER_PARTLY]}, "
                    f"no {counts[ANSWER_NO]}, rather not say {counts[ANSWER_RATHER_NOT_SAY]}"
                )
            answered = sum(counts.values())
            self.stdout.write(f"  {key}: {answered} answered — {summary}")

    def _demographics(self, minimum: int):
        self.stdout.write("\nCensus (cells below the threshold are refused, not dropped)")
        rows = list(
            SelfCheckDemographic.objects.values(
                "census_gender", "census_age_band", "census_demographic_group"
            )
        )
        for column, label in (
            ("census_gender", "Gender"),
            ("census_age_band", "Age group"),
            ("census_demographic_group", "Demographic group"),
        ):
            counts = Counter(row[column] for row in rows if row.get(column))
            self.stdout.write(f"  {label}")
            if not counts:
                self.stdout.write("    (nobody answered)")
                continue
            released = [pair for pair in counts.most_common() if pair[1] >= minimum]
            withheld = len(counts) - len(released)
            for value, count in released:
                self.stdout.write(f"    {value}: {count}")
            if withheld:
                # Naming the value *and* its count would publish the cell this threshold exists
                # to protect: "Female: 1" is the person. The refusal names neither.
                self.stdout.write(
                    f"    {withheld} cell(s) not shown — fewer than {minimum} in the cell"
                )
