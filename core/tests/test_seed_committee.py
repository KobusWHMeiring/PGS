"""Task A2 — committee positions and the 2026 roster.

Two facts from the OPP drive this file:

1. **A committee position is a term, not an attribute** (spec §3.2). Composition is
   renewed at every AGM, so `CommitteeTerm` carries `agm_year` and `vacated_on`
   rather than a `User.is_committee` flag. The same person holds several positions
   at once (Sasha Mentz is Chairperson *and* does farm visit administration;
   Rebecca Dixon is Secretary *and* Communications), so a holder is not unique.
2. **Vacancy is a representable state** (spec §3.2). Events coordination and
   academic representation are advertised as open, not omitted. A missing row and a
   vacant seat mean different things to a reviewer.

The roster is seeded from **OPP §VII, page 12 of the reviewed corpus**
(`knowledge/corpus/opp.md`), not from the plan's summary of it.

One deliberate absence: the OPP says the roster was agreed *"during the PGS's AGM
held in 2025"* and names no date. `elected_on` is therefore left null rather than
filled with an invented day — a false precise date in an evidentiary table is worse
than an admitted gap. `test_election_date_is_left_null_because_the_opp_names_only_a_year`
exists to stop the next person "tidying" it.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from core.models import CommitteePosition, CommitteeTerm
from core.services._seed import seed_deployment

pytestmark = pytest.mark.django_db

AGM_YEAR = 2026


def _terms():
    return CommitteeTerm.objects.filter(agm_year=AGM_YEAR)


def _holders(position: str) -> list[str]:
    return list(
        _terms()
        .filter(position=position)
        .order_by("holder_name")
        .values_list("holder_name", flat=True)
    )


# --- The plan's named tests ---------------------------------------------------


def test_seeding_twice_creates_no_duplicates():
    seed_deployment()
    first = _terms().count()
    assert first > 0
    seed_deployment()
    assert _terms().count() == first


def test_events_coordination_and_academic_representation_exist_as_vacant():
    # "Vacant, advertised as a call for expressions of interest" (spec §3.2) — a row
    # with no holder, not a missing row.
    seed_deployment()
    for position in (
        CommitteePosition.EVENTS_COORDINATION,
        CommitteePosition.ACADEMIC_REPRESENTATIVE,
    ):
        rows = _terms().filter(position=position)
        assert rows.count() == 1, position
        assert rows.get().is_vacant is True, position


def test_position_accepts_exactly_the_eleven_opp_values():
    # spec §3.2, OPP §3.1. Exactly eleven; the list is the clause, so a change here
    # is a change to the standard and not a tidy-up.
    assert CommitteePosition.values == [
        "CHAIRPERSON",
        "VICE_CHAIRPERSON",
        "SECRETARY",
        "TREASURER",
        "FARM_VISIT_ADMINISTRATION",
        "TECHNICAL_FARMING_SUPPORT",
        "COMMUNICATIONS",
        "EVENTS_COORDINATION",
        "CONSUMER_REPRESENTATIVE",
        "RETAIL_MARKET_REPRESENTATIVE",
        "ACADEMIC_REPRESENTATIVE",
    ]


def test_a_position_outside_the_clause_is_rejected(member):
    # Validation, not integrity (testing_hazards §1.7): a CharField with choices is
    # enforced by full_clean(), never by the database.
    term = CommitteeTerm(
        user=member.user,
        holder_name="Someone",
        position="HEAD_OF_EVERYTHING",
        agm_year=AGM_YEAR,
    )
    with pytest.raises(ValidationError) as exc:
        term.full_clean()
    assert "position" in exc.value.message_dict


# --- The roster as the OPP prints it -----------------------------------------


def test_the_roster_matches_opp_section_seven():
    seed_deployment()
    assert _holders(CommitteePosition.CHAIRPERSON) == ["Sasha Mentz"]
    assert _holders(CommitteePosition.VICE_CHAIRPERSON) == ["Alison Evans"]
    assert _holders(CommitteePosition.SECRETARY) == ["Rebecca Dixon"]
    assert _holders(CommitteePosition.TREASURER) == ["Van Wyk Pretorius"]


def test_farm_visit_administration_holds_four_people():
    # OPP §VII: "Sasha Mentz; Nina Wardman; Avril Dawson; Tony" — four holders, and
    # one position. A schema with one holder per position could not record this.
    seed_deployment()
    assert _holders(CommitteePosition.FARM_VISIT_ADMINISTRATION) == [
        "Avril Dawson",
        "Nina Wardman",
        "Sasha Mentz",
        "Tony",
    ]


def test_one_person_can_hold_two_positions():
    # Not an accident in the roster: Sasha Mentz chairs and does farm visit
    # administration; Rebecca Dixon is Secretary and Communications.
    seed_deployment()
    assert "Rebecca Dixon" in _holders(CommitteePosition.SECRETARY)
    assert "Rebecca Dixon" in _holders(CommitteePosition.COMMUNICATIONS)
    assert "Nina Wardman" in _holders(CommitteePosition.RETAIL_MARKET_REPRESENTATIVE)


def test_election_date_is_left_null_because_the_opp_names_only_a_year():
    # OPP §VII: "agreed during the PGS's AGM held in 2025". No day or month exists in
    # the source. Filling one in would put a fabricated date into evidentiary data.
    seed_deployment()
    assert {t.elected_on for t in _terms()} == {None}


# --- The two rules seeding must not break ------------------------------------


def test_reseeding_does_not_un_vacate_a_seated_holder():
    # The `is_active`-on-seals rule, applied to people. The holder stood down; the row
    # keeps its position, year and name — i.e. its natural key — and gains vacated_on.
    # A deploy must not put them back.
    #
    # This test was first written by *renaming* the holder, which quietly changed the
    # natural key and so could not detect an overwrite at all: it passed against a
    # seeder that cleared vacated_on. Mutation testing on the seeder caught it. The
    # guard only works if the row still matches what the seeder will look for.
    seed_deployment()
    seat = _terms().get(
        position=CommitteePosition.CHAIRPERSON, holder_name="Sasha Mentz"
    )
    seat.vacated_on = "2027-03-31"
    seat.save()

    seed_deployment()

    seat.refresh_from_db()
    assert str(seat.vacated_on) == "2027-03-31"


def test_reseeding_leaves_a_filled_seat_alone():
    # The other direction: a seat the group has filled must not be reseeded back to
    # vacant. The vacant row is the natural key's blank name, so filling it creates a
    # second row and the original stays as the record of the open seat.
    seed_deployment()
    seat = _terms().get(position=CommitteePosition.EVENTS_COORDINATION)
    seat.holder_name = "Nomsa Filled"
    seat.save()

    seed_deployment()

    seat.refresh_from_db()
    assert seat.holder_name == "Nomsa Filled"
    assert seat.is_vacant is False


def test_committee_terms_carry_no_contact_details():
    # The plan's instruction, made structural: a position is a public governance fact,
    # and there is nowhere on the row to put a phone number.
    field_names = {f.name for f in CommitteeTerm._meta.get_fields()}
    assert not field_names & {"phone", "email", "mobile", "address"}


# --- The acceptance criterion ------------------------------------------------


def test_seed_deployment_seeds_categories_seals_and_committee_terms():
    result = seed_deployment()
    # The result is a contract: one key per thing a deployment seeds, so a new data set
    # that forgets to report itself is visible here (A5 added the turnover scale).
    assert set(result) == {
        "standard_sets",
        "seals",
        "categories",
        "turnover_bands",
        "committee_terms",
    }
    created, _updated = result["committee_terms"]
    assert created == len(_terms()) == 15
