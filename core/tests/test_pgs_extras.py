"""`pgs_extras` — template-side formatting, which is the only place money is a string.

`build_principles.md` §III: money is stored and calculated as **integer cents**
(`Int`, `*_cents`), and `format_zar(cents: int) -> str` is the one function that turns
those integers into something a person reads. Nothing else may format money, which is
why the public site's fee figures all pass through here: if the ribbon and the fee
table used different format strings, they would eventually disagree.

The prototype writes `1 500` with a space as the thousands separator and no
decimals — the South African convention, and what the OPP itself uses once its
commas are normalised. `R100`, never `R100.00`.
"""

from __future__ import annotations

import pytest

from core.templatetags.pgs_extras import format_zar


@pytest.mark.parametrize(
    ("cents", "expected"),
    [
        (10_000, "R100"),
        (50_000, "R500"),
        (90_000, "R900"),
        (150_000, "R1 500"),
        (320_000, "R3 200"),
        (800_000, "R8 000"),
        (0, "R0"),
    ],
)
def test_format_zar_renders_rands_without_decimals(cents: int, expected: str):
    assert format_zar(cents) == expected


def test_format_zar_keeps_cents_when_they_exist():
    """Whole rand is the common case, not the only case. Dropping the remainder
    silently would under-report a fee by up to R0.99."""
    assert format_zar(10_050) == "R100.50"
    assert format_zar(1) == "R0.01"


def test_format_zar_handles_the_sign():
    assert format_zar(-10_000) == "-R100"


def test_format_zar_refuses_a_float():
    """§III: "Never `FloatField` for money." A float reaching the formatter is a
    rounding bug in waiting — 0.1 + 0.2 is not 0.3 — so it is refused loudly rather
    than coerced. `round()` here would hide the caller's defect."""
    with pytest.raises(TypeError):
        format_zar(100.0)  # type: ignore[arg-type]


def test_format_zar_refuses_a_bool():
    """`True` is an `int` in Python and would render as `R0.01`.

    A boolean arriving where cents belong means a caller passed `is_paid_up` instead
    of a fee, and the failure must be visible rather than plausible.
    """
    with pytest.raises(TypeError):
        format_zar(True)  # type: ignore[arg-type]


def test_format_zar_is_also_registered_as_a_template_filter():
    """The templates call `{{ cents|zar }}`; the filter must be the same function,
    or the tested behaviour and the rendered behaviour are two different things."""
    from core.templatetags import pgs_extras

    assert pgs_extras.zar(150_000) == format_zar(150_000)
