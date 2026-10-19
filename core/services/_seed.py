"""Deployment seeding: the group's data, applied idempotently.

`build_principles.md` §I: *code encodes the PGS process; data encodes the standard
and the group.* This module is the boundary. Everything it writes is **data** —
seals, categories, and (in later increments) group identity and the standard set —
so that retargeting to another standard or PGS group is a seed change, not a
migration.

Two properties are non-negotiable, and both are asserted by
`core/tests/test_seed_deployment.py`:

1. **Idempotent.** Re-running on every deploy is the intended usage, so a row that
   already exists is updated in place, never duplicated.
2. **It does not resurrect a deliberate decision.** `is_active` is applied on
   *create* only. If the group retires a seal, a later release's `seed_deployment`
   must not silently switch it back on and resume publishing a claim. This is the
   one place where "idempotent" and "declarative" disagree, and correctness wins.

Source of truth for every row below is the shipped OPP
(`pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf`), verified
against the PDF rather than against a plan — see HANDOVER §1.7.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from core.models import Category, Seal


@dataclass(frozen=True)
class SealSpec:
    """One seal as the standard defines it.

    `is_active` here is the *default for a fresh deployment*. It is applied on
    create only — see `_seed_seals`.
    """

    code: str
    label: str
    standard_ref: str
    is_active: bool
    criteria_defined: bool
    display_note: str = ""


@dataclass(frozen=True)
class CategorySpec:
    code: str
    label: str
    display_order: int
    is_active: bool
    standard_ref: str


# --- The deployed Outeniqua set ---------------------------------------------
#
# Seals: OPP §V, "Seals and certificates issued by the PGS committee", which reads
# "The following certificates may be issued to the farmer" and lists exactly three.

SEALS: tuple[SealSpec, ...] = (
    SealSpec(
        code="PGS_ORGANIC_CERTIFIED",
        label="PGS Organic Certified",
        standard_ref="OPP §V",
        is_active=True,
        criteria_defined=True,
        display_note=(
            "Farmers who are fully compliant with the SAOSO organic standard may be "
            "issued this seal. DALRRD stipulates that any product labelled 'organic' "
            "must be substantiated by proof of organic status."
        ),
    ),
    SealSpec(
        code="PGS_ORGANIC_IN_CONVERSION",
        label="PGS Organic In-Conversion",
        standard_ref="OPP §V",
        is_active=True,
        criteria_defined=True,
        display_note=(
            "For farmers who cannot attest to the organic history of the land or are "
            "converting from chemical to organic agriculture: land under organic "
            "management for less than 18 months before sowing or planting (annuals), "
            "12 months before grazing or harvest (pastures and meadows), or 12 months "
            "before harvest (other perennials). Also usable where corrective action is "
            "required following a deviation."
        ),
    ),
    SealSpec(
        code="PGS_PASTURE_RAISED",
        label="PGS pasture-raised",
        standard_ref="OPP §V",
        # D11 / F3. NOT SHIPPED. OPP §V states its criteria are "details on this
        # forthcoming". Issuance is blocked unconditionally (see
        # core/services/_certification.py) and the seal is never rendered publicly.
        # Enabling it when the national working group publishes criteria is a seed
        # change — that is the whole point of it being a row.
        is_active=False,
        criteria_defined=False,
        display_note=(
            "OPP §V: \"Pasture raised is not defined by the SAOSO standard - details "
            "on this forthcoming.\" The mark is authorised but its criteria are not "
            "published, so it cannot be substantiated to a consumer and this "
            "deployment does not issue it."
        ),
    ),
)


# Categories: spec §4.1. FORM Sheets F/G/H mark the last three *in development*;
# they are seeded inactive rather than omitted, so publishing them later is a data
# change and the schema never needs a migration for a new category.

CATEGORIES: tuple[CategorySpec, ...] = (
    CategorySpec("CROPS", "Crops", 10, True, "FORM Sheet B.1"),
    CategorySpec("ANIMAL_HUSBANDRY", "Animal Husbandry", 20, True, "FORM Sheet C"),
    CategorySpec("SEED_PRODUCTION", "Seed Production", 30, True, "FORM Sheet D"),
    CategorySpec("AGRO_PROCESSING", "Agro-processing", 40, True, "FORM Sheet E"),
    # --- in development -----------------------------------------------------
    CategorySpec("AQUACULTURE", "Aquaculture", 50, False, "FORM Sheet F (in development)"),
    CategorySpec("WINE", "Wine", 60, False, "FORM Sheet G (in development)"),
    CategorySpec(
        "INPUT_SUPPLIER", "Input Supplier", 70, False, "FORM Sheet H (in development)"
    ),
)


def _seed_seals() -> tuple[int, int]:
    """Create-or-update seals. Returns (created, updated).

    `is_active` is set **on create only**. A deployment that has retired a seal must
    not have it silently reactivated by the next release — see the module docstring.
    """
    created = updated = 0
    for spec in SEALS:
        seal, was_created = Seal.objects.get_or_create(
            code=spec.code,
            defaults={
                "label": spec.label,
                "standard_ref": spec.standard_ref,
                "is_active": spec.is_active,
                "criteria_defined": spec.criteria_defined,
                "display_note": spec.display_note,
            },
        )
        if was_created:
            created += 1
            continue

        # Descriptive fields track the source document, so they are refreshed.
        seal.label = spec.label
        seal.standard_ref = spec.standard_ref
        seal.criteria_defined = spec.criteria_defined
        seal.display_note = spec.display_note
        seal.save(update_fields=["label", "standard_ref", "criteria_defined", "display_note"])
        updated += 1
    return created, updated


def _seed_categories() -> tuple[int, int]:
    """Create-or-update categories, preserving a deployment's own `is_active`."""
    created = updated = 0
    for spec in CATEGORIES:
        category, was_created = Category.objects.get_or_create(
            code=spec.code,
            defaults={
                "label": spec.label,
                "display_order": spec.display_order,
                "is_active": spec.is_active,
                "standard_ref": spec.standard_ref,
            },
        )
        if was_created:
            created += 1
            continue

        category.label = spec.label
        category.display_order = spec.display_order
        category.standard_ref = spec.standard_ref
        category.save(update_fields=["label", "display_order", "standard_ref"])
        updated += 1
    return created, updated


@transaction.atomic
def seed_deployment() -> dict[str, tuple[int, int]]:
    """Apply the group's data. Safe to run on every deploy.

    In: none.
    Out: `{"seals": (created, updated), "categories": (created, updated)}`.
    Side Effects: writes `Seal` and `Category` rows. Does **not** change `is_active`
         on rows that already exist.
    Fails: never deliberately; a database error propagates. The whole seed is one
         transaction, so a partial deployment state is not reachable.
    Idempotency: yes — this is the requirement, not a nicety, because it runs on
         every release.
    """
    return {
        "seals": _seed_seals(),
        "categories": _seed_categories(),
    }
