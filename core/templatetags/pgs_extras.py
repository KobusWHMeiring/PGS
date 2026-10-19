"""Template tags and filters — the boundary where values become strings.

`build_principles.md` §III is the rule this module exists for:

* money is stored and calculated as **integer cents** (`Int`) with a `_cents` suffix;
* **formatting happens at the boundary only**, in `format_zar()`.

Everything the public site renders about fees therefore passes through one function.
That is not tidiness: the key-facts ribbon and the fee table show the same R100, and
if either formatted its own figure they would eventually disagree — one of them
having been edited at midnight before an AGM.
"""

from __future__ import annotations

from django import template

register = template.Library()

#: South African convention: `R1 500`, space-separated thousands, no decimals unless
#: there are cents to show. The OPP prints `R 250,000`; the design and the group's
#: own pages print `R250 000`. The design's convention wins because it is what
#: members already read on the live site.
_THOUSANDS_SEPARATOR = " "


def format_zar(cents: int) -> str:
    """Format integer cents as rand for display.

    In:      `cents` — an `int`. Floats and bools are **refused**, not coerced:
             §III forbids floats for money, and `True` is an `int` in Python that
             would otherwise render as `R0.01`. Both mean a caller passed the wrong
             thing, and a loud `TypeError` is cheaper than a wrong invoice.
    Out:     a string such as `R100`, `R1 500`, `R800.50`, `-R100`.
    Fails:   `TypeError` on a non-int (including `bool`).
    """
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise TypeError(
            f"format_zar expects integer cents, got {type(cents).__name__} — "
            "money is stored as integers (build_principles.md §III)"
        )

    sign = "-" if cents < 0 else ""
    rands, remainder = divmod(abs(cents), 100)
    whole = f"{rands:,}".replace(",", _THOUSANDS_SEPARATOR)

    if remainder:
        return f"{sign}R{whole}.{remainder:02d}"
    return f"{sign}R{whole}"


@register.filter(name="zar")
def zar(cents: int) -> str:
    """`{{ fee_cents|zar }}` — the same function, so the test and the template agree."""
    return format_zar(cents)
