"""B1's acceptance check on the **migration itself**, not on the models.

`MVP0_PLAN_V2.md` B1: "migration applies; `VectorExtension()` is created before the
vector column." That is a property of the migration file, and it is checked by
reading it — the same reason A7 parses `.importlinter` instead of trusting an exit
code (testing_hazards.md §2.1). A tool can be green and enforce nothing.

This lives in its own module, without `pytest.mark.django_db`, on purpose: with the
mark, a mutated migration fails during test-database creation (`type "vector" does
not exist`) and the *assertion* never runs. The guard has to fail for its own stated
reason, or a future reader learns the wrong lesson from the traceback.

Measured, with the mutation applied (extension moved after the column):

    django.db.utils.ProgrammingError: type "vector" does not exist
    LINE 1: ... "embedding" vector(768) ...

i.e. a clean checkout cannot migrate — while a dev box where the extension was
installed by hand would migrate happily and never notice.
"""

from __future__ import annotations

from pathlib import Path

MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "0001_initial.py"


def test_vector_extension_precedes_the_embedding_column():
    source = MIGRATION.read_text(encoding="utf-8")
    assert "VectorExtension()" in source, "the extension is never created"
    assert source.index("VectorExtension()") < source.index(
        "'embedding'"
    ), "VectorExtension() comes after the embedding column — a clean checkout cannot migrate"


def test_embedding_column_width_matches_the_migration():
    """The frozen dimension is in the migration; a `settings` change without one is a lie.

    `test_models.test_embedding_dimension_matches_settings` asserts the field agrees
    with settings at import time. This asserts the *migration* agrees too, so raising
    `EMBEDDING_DIM` in `.env` cannot appear to work on a database that was created
    before the change.
    """
    from django.conf import settings

    source = MIGRATION.read_text(encoding="utf-8")
    assert f"dimensions={settings.EMBEDDING_DIM}" in source
