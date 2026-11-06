"""`load_template` — import an assessment questionnaire from a file (spec §4.9, D28).

The template is data (§4.8), so this command is the only way a questionnaire enters the platform.
Three rules make it safe to run on every deploy:

1. **Validate before writing.** Every problem is printed, and a file with one problem writes nothing:
   a questionnaire the validator has not passed must not become the thing a visit captures answers
   against.
2. **Never overwrite a version.** A template that exists is history — an assessment freezes a *copy*
   of its schema at visit creation, so editing a row in place would rewrite the meaning of every past
   visit that used it. So a file whose schema differs from the stored one is a **command error**:
   the fix is a new `version` in the file, not a silent update. A re-run of an unchanged file is a
   successful no-op, which is what makes the command re-runnable in a deploy.
3. **Activation is explicit** (`--activate`) and goes through `activate_template`, which stands the
   previous version of that category down. Loading a template does not make it live by accident.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.models import AssessmentTemplate, Category
from core.services._templates import activate_template, assert_valid_schema


class Command(BaseCommand):
    help = "Import an AssessmentTemplate JSON file (spec §4.9). Validates; never overwrites a version."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to a template JSON file, e.g. core/templates_data/crops.v1.json")
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Make this version the category's live template, standing the previous one down.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        schema = self._read(path)
        category = self._category(schema, path)
        version = self._required(schema, "version", path)
        standard_version = self._required(schema, "standard_version", path)

        try:
            assert_valid_schema(schema)
        except Exception as exc:  # SchemaValidationError, so every problem can be printed
            problems = getattr(exc, "problems", None)
            if problems is None:
                raise
            self.stderr.write(self.style.ERROR(f"{path}: {len(problems)} problem(s), nothing written:"))
            for problem in problems:
                self.stderr.write(f"  - {problem}")
            raise CommandError(f"{path} did not validate") from exc

        existing = AssessmentTemplate.objects.filter(category=category, version=version).first()
        if existing is None:
            template = AssessmentTemplate.objects.create(
                category=category,
                version=version,
                standard_version=standard_version,
                schema=schema,
                effective_from=schema.get("effective_from") or _today(),
            )
            self.stdout.write(self.style.SUCCESS(f"created {category.code}:{version}"))
        elif existing.schema != schema:
            raise CommandError(
                f"{category.code}:{version} already exists with a different schema. A template that "
                "exists is history — every past assessment froze a copy of it. Bump `version` in the "
                "file and load that instead; nothing was written."
            )
        else:
            template = existing
            self.stdout.write(f"{category.code}:{version} already loaded, unchanged")

        if options["activate"]:
            activate_template(template)
            self.stdout.write(self.style.SUCCESS(f"activated {category.code}:{version}"))

    # --- parsing ----------------------------------------------------------

    def _read(self, path: Path) -> dict:
        if not path.is_file():
            raise CommandError(f"{path} does not exist")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"{path} is not valid JSON: {exc}") from exc

    def _category(self, schema: dict, path: Path) -> Category:
        code = self._required(schema, "category", path)
        category = Category.objects.filter(code=code).first()
        if category is None:
            known = sorted(Category.objects.values_list("code", flat=True))
            raise CommandError(
                f"{path}: category {code!r} is not seeded on this deployment (known: {known}). "
                "Categories are data — `seed_deployment` creates them."
            )
        return category

    def _required(self, schema: dict, key: str, path: Path) -> str:
        value = schema.get(key)
        if not isinstance(value, str) or not value.strip():
            raise CommandError(
                f"{path}: `{key}` is required at the top level (the schema names its own category, "
                "version and standard so a file cannot be loaded into the wrong place)"
            )
        return value.strip()


def _today():
    from django.utils import timezone

    return timezone.localdate()
