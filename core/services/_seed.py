"""Deployment seeding: the group's data, applied idempotently.

`build_principles.md` §I: *code encodes the PGS process; data encodes the standard
and the group.* This module is the boundary. Everything it writes is **data** —
seals, categories, the turnover scale, and (in later increments) group identity and the
standard set — so that retargeting to another standard or PGS group is a seed change, not
a migration.

Two properties are non-negotiable, and both are asserted by
`core/tests/test_seed_deployment.py`:

1. **Idempotent.** Re-running on every deploy is the intended usage, so a row that
   already exists is updated in place, never duplicated.
2. **It does not resurrect a deliberate decision.** `is_active` is applied on
   *create* only, and so are `TurnoverBand.initial_fee_cents` / `renewal_fee_cents`. If
   the group retires a seal, a later release's `seed_deployment` must not silently switch
   it back on and resume publishing a claim; if the AGM changes a fee, a release must not
   re-price a band that members have already been invoiced against. This is the
   one place where "idempotent" and "declarative" disagree, and correctness wins.

Source of truth for every row below is the shipped OPP
(`pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf`), verified
against the PDF rather than against a plan — see HANDOVER §1.7.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from core.models import (
    Category,
    CommitteePosition,
    CommitteeTerm,
    ConsentPurpose,
    ConsentText,
    Seal,
    TurnoverBand,
)
from knowledge.models import StandardSet


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
# The **StandardSet** is group data, not code (D16, §4.5): it groups the four governed
# documents so retrieval can be scoped to them and so two corpora (SAOSO 2.1 beside
# 2.2) can coexist. It belongs here for the same reason the seals do, and SPEC §4.5's
# seeding note already promised it — `ingest_standard` refuses to guess a set, so
# without this row a fresh deployment cannot ingest anything at all.

STANDARD_SET_CODE = "outeniqua"
STANDARD_SET_LABEL = "Outeniqua PGS corpus"
STANDARD_SET_DESCRIPTION = (
    "The four governed documents (D16): the SAOSO Standard v2.1, the Outeniqua PGS "
    "Principles, Policies and Procedures, the Basic Production Principles, and the "
    "South African organic certification landscape. Retrieval is always scoped to a "
    "set (§4.5), so a chatbot answering about SAOSO cannot cite another standard."
)

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


# --- The 2026 committee (OPP §VII, page 12) ----------------------------------
#
# Read from the reviewed corpus (`knowledge/corpus/opp.md`), not from the plan's
# summary of it. `holder_name` is the printed name; parentheticals in the source are
# support relationships ("with support from Lilani Pretorius", "Wild Oats"), not
# second holders, so they are not rows.
#
# A blank name is a **vacancy** (spec §3.2), not an omission: the OPP advertises both
# seats as open. `elected_on` is left None throughout because the source says only
# "the AGM held in 2025" — no day, no month. `vacated_on` is never written here; see
# `_seed_committee_terms`.

COMMITTEE_AGM_YEAR = 2026

COMMITTEE_ROSTER: tuple[tuple[str, str], ...] = (
    (CommitteePosition.CHAIRPERSON, "Sasha Mentz"),
    (CommitteePosition.VICE_CHAIRPERSON, "Alison Evans"),
    (CommitteePosition.SECRETARY, "Rebecca Dixon"),
    (CommitteePosition.TREASURER, "Van Wyk Pretorius"),
    # Four people, one position — the reason the natural key includes the holder.
    (CommitteePosition.FARM_VISIT_ADMINISTRATION, "Sasha Mentz"),
    (CommitteePosition.FARM_VISIT_ADMINISTRATION, "Nina Wardman"),
    (CommitteePosition.FARM_VISIT_ADMINISTRATION, "Avril Dawson"),
    (CommitteePosition.FARM_VISIT_ADMINISTRATION, "Tony"),
    (CommitteePosition.TECHNICAL_FARMING_SUPPORT, "Robyn"),
    (CommitteePosition.COMMUNICATIONS, "Rebecca Dixon"),
    (CommitteePosition.EVENTS_COORDINATION, ""),  # TBC — call for expressions of interest
    (CommitteePosition.CONSUMER_REPRESENTATIVE, "Avril Dawson"),
    (CommitteePosition.RETAIL_MARKET_REPRESENTATIVE, "Charlene"),
    (CommitteePosition.RETAIL_MARKET_REPRESENTATIVE, "Nina Wardman"),
    (CommitteePosition.ACADEMIC_REPRESENTATIVE, ""),  # TBC — call for expressions of interest
)


def _seed_committee_terms() -> tuple[int, int]:
    """Create the 2026 committee terms. Returns (created, updated).

    **`vacated_on` is never written.** It is created null and then left alone, for the
    same reason `is_active` on seals is applied on create only: once the group records
    that a holder stood down, a deploy must not quietly put the seat back. A seat the
    group has filled is also left alone — `holder_name` is the natural key, so
    re-seeding an empty seat creates the vacant row again only if someone deleted it,
    which is a different event and should be visible.
    """
    created = updated = 0
    for position, holder_name in COMMITTEE_ROSTER:
        term, was_created = CommitteeTerm.objects.get_or_create(
            position=position,
            agm_year=COMMITTEE_AGM_YEAR,
            holder_name=holder_name,
        )
        if was_created:
            created += 1
            continue
        # Nothing to refresh: every stored field of a term is either the natural key
        # or a fact about a person that the seeder must not overwrite.
        updated += 1
    return created, updated


def _seed_standard_set() -> tuple[int, int]:
    """Create the corpus set, or refresh an existing one's description.

    `is_default` is applied **on create only**, for the same reason `is_active` is on
    seals: a deployment that has deliberately made another set the default — while
    loading SAOSO 2.2 beside 2.1, say — must not have that choice undone by a release.
    """
    standard_set, was_created = StandardSet.objects.get_or_create(
        code=STANDARD_SET_CODE,
        defaults={
            "label": STANDARD_SET_LABEL,
            "description": STANDARD_SET_DESCRIPTION,
            "is_default": True,
        },
    )
    if was_created:
        return 1, 0

    # Descriptive fields track the deployment's own corpus, so they are refreshed.
    standard_set.label = STANDARD_SET_LABEL
    standard_set.description = STANDARD_SET_DESCRIPTION
    standard_set.save(update_fields=["label", "description"])
    return 0, 1


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


@dataclass(frozen=True)
class ConsentTextSpec:
    """One version of one consent, exactly as the group wrote it.

    `body` is plain text with blank lines between paragraphs, rendered with `linebreaks`
    so a group can add a paragraph without a template change. The `[DECIDE: …]` markers
    are **the point**, not leftovers: SELF_CHECK_PRD §11.6 names the retention period and
    the address to write to as the group's answers, and a page that quietly invented
    either would put a promise in a consent text the group has not made.
    """

    purpose: str
    version: str
    heading: str
    body: str


#: Q8's third consent (SELF_CHECK_PRD §11.6, written 2026-11-05). `approved_at` is left
#: null by the seed: this is a **draft to correct**, and the interface must say so.
ACCOUNT_CONSENT = ConsentTextSpec(
    purpose=ConsentPurpose.ACCOUNT,
    version="account-2026-11-05",
    heading="May we keep your details so you can come back to this?",
    body="""
We hold your name, how to reach you, your farm's name and nearest town, and who to speak to about a visit. We use them to keep your application in one place and to contact you about it — nothing else. The committee and the administrator can see them; nobody outside the group can, and we never publish them. We keep them while your account is open and for [DECIDE: proposed 12 months] after the last time you contacted us, then we delete them. You can ask us to delete them at any time by writing to [DECIDE: the administrator's email/phone — not yet published], and we will do it within 30 days.

This is not the research question and not the census question. Research consent asks whether your answers may be counted in totals for PGS South Africa and SAOSO; the demographic question asks whether census details may be counted too. This one is about the account itself — the name, contact and farm details the group needs in order to keep a conversation with you about an application.

It is a consent to hold and to contact, never to publish. A public farm profile is a separate consent you would give later, and leaving this unticked refuses nothing else: only the account, because an account is the thing that needs your details to exist.
""".strip(),
)

CONSENT_TEXTS: tuple[ConsentTextSpec, ...] = (ACCOUNT_CONSENT,)


def _seed_consent_texts() -> tuple[int, int]:
    """Create any consent wording the deployment does not have. Returns (created, updated).

    **Create-only, and `updated` is always 0 — that is the rule, not an omission.** A
    consent is versioned, not edited (`ConsentText`): changing a body in place would
    change the meaning of every record that points at it, which is exactly what a version
    exists to prevent. New wording is a new `version` row, and the group's approval is a
    later act on the same row (`approved_at`), so neither is overwritten by a deploy.
    """
    created = updated = 0
    for spec in CONSENT_TEXTS:
        _, was_created = ConsentText.objects.get_or_create(
            purpose=spec.purpose,
            version=spec.version,
            defaults={"heading": spec.heading, "body": spec.body},
        )
        created += int(was_created)
        updated += int(not was_created)
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


@dataclass(frozen=True)
class TurnoverBandSpec:
    """One row of OPP §2.3's sliding scale.

    `max_turnover_cents=None` means open-ended. Bounds are half-open — `min` inclusive,
    `max` exclusive — because the printed table reads "Below R 250,000" and then
    "R 250,001 – R 500,000", which leaves R250,000.50 in neither (see `TurnoverBand`).
    `initial_fee_cents` and `renewal_fee_cents` are applied on create only: the AGM sets
    prices, and a release must not re-price a fee a member was already invoiced for.
    """

    code: str
    label: str
    min_turnover_cents: int
    max_turnover_cents: int | None
    initial_fee_cents: int
    renewal_fee_cents: int


# OPP §2.3, "PGS assessment fee structure (initial certification and renewal)", printed
# with the table's own wording in `label`. Rand in the document, cents in the schema (§III).
TURNOVER_BANDS: tuple[TurnoverBandSpec, ...] = (
    TurnoverBandSpec("B1", "Below R 250,000", 0, 25_000_000, 150_000, 90_000),
    TurnoverBandSpec("B2", "R 250,001 – R 500,000", 25_000_000, 50_000_000, 250_000, 200_000),
    TurnoverBandSpec("B3", "R 500,001 – R 1,000,000", 50_000_000, 100_000_000, 300_000, 250_000),
    TurnoverBandSpec("B4", "R 1,000,001 – R 2,500,000", 100_000_000, 250_000_000, 370_000, 320_000),
    TurnoverBandSpec("B5", "R 2,500,001 – R 5,000,000", 250_000_000, 500_000_000, 500_000, 500_000),
    TurnoverBandSpec("B6", "Above R 5,000,000", 500_000_000, None, 800_000, 800_000),
)


def _seed_turnover_bands() -> tuple[int, int]:
    """Create-or-update the OPP §2.3 scale. Returns (created, updated).

    The band's *structure* (label, bounds, order) is the printed document, so it is
    refreshed on every deploy — a corrected table reaches an existing deployment. The
    *prices* are the group's AGM decision, so they are set on create only: a release that
    silently re-priced a band would change what a member was invoiced after the invoice
    went out.
    """
    created = updated = 0
    for order, spec in enumerate(TURNOVER_BANDS, start=1):
        band, was_created = TurnoverBand.objects.get_or_create(
            code=spec.code,
            defaults={
                "label": spec.label,
                "min_turnover_cents": spec.min_turnover_cents,
                "max_turnover_cents": spec.max_turnover_cents,
                "initial_fee_cents": spec.initial_fee_cents,
                "renewal_fee_cents": spec.renewal_fee_cents,
                "display_order": order,
            },
        )
        if was_created:
            created += 1
            continue

        band.label = spec.label
        band.min_turnover_cents = spec.min_turnover_cents
        band.max_turnover_cents = spec.max_turnover_cents
        band.display_order = order
        band.save(update_fields=["label", "min_turnover_cents", "max_turnover_cents", "display_order"])
        updated += 1
    return created, updated


@transaction.atomic
def seed_deployment() -> dict[str, tuple[int, int]]:
    """Apply the group's data. Safe to run on every deploy.

    In: none.
    Out: `{"standard_sets": …, "seals": (created, updated), "categories": …,`
         `"turnover_bands": …, "committee_terms": (created, updated),`
         `"consent_texts": (created, updated)}`.
    Side Effects: writes `StandardSet`, `Seal`, `Category`, `TurnoverBand`,
         `CommitteeTerm` and `ConsentText` rows.
         Does **not** change `is_active` on seals, `is_default` on the set, or
         `vacated_on` on a committee term, once they exist.
    Fails: never deliberately; a database error propagates. The whole seed is one
         transaction, so a partial deployment state is not reachable.
    Idempotency: yes — this is the requirement, not a nicety, because it runs on
         every release.
    """
    return {
        "standard_sets": _seed_standard_set(),
        "seals": _seed_seals(),
        "categories": _seed_categories(),
        "turnover_bands": _seed_turnover_bands(),
        "committee_terms": _seed_committee_terms(),
        "consent_texts": _seed_consent_texts(),
    }
