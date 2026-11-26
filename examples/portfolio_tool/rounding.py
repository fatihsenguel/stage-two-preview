"""
The one rounding to the cent: half-up, on the decimal a figure prints as
(decision 76's first part; KNOWN_GAPS J1). 18,083.175 is 18,083.18, where
the float format gives the binary neighbour's .17 (decision 75).

Read by the window return's printer, the policy check's distances and the
P/E (quant/multiples.py), which rounded half to even until 6 October 2026:
Part 19's nineteen P/E print the same both ways; by nodes.py's money,
prices and percents, its records carrying the money unrounded; and by the
chart's P/E labels, the watch's close and range and a proposal's percent.
The statistics stay float. `as_decimal` is the one reading of a stored
figure as a decimal, where the arithmetic in decimal starts: the ledger
(decision 76's last part). `as_stated` prints a figure the owner or a
document stated, a policy limit or a threshold, as stated and not
rounded; `to_places` rounds half-up to any number of places, the cent
being two. The statistics, the timings, a model call's cost and the logs'
other figures stay floats: they are not figures about the portfolio, the
policy or a company. Held by tests/test_rounding.py.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Union

__all__ = ["CENT", "as_decimal", "as_stated", "to_cent", "to_percent", "to_places"]

CENT = Decimal("0.01")


def to_places(value: Union[Decimal, float], places: int) -> Decimal:
    """`value` to `places` decimals, half-up, on the decimal it prints as:
    a distance in points to two or four, a rate to four, a filed amount to
    whole units."""
    return as_decimal(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def to_cent(value: Union[Decimal, float]) -> Decimal:
    """`value` to the cent, half-up; a float, NumPy's or an int among them,
    is read as the decimal it prints as."""
    return to_places(value, 2)


def to_percent(value: Union[Decimal, float], signed: bool = False) -> str:
    """A share printed as a percent to the hundredth, half-up, multiplied by
    100 in decimal, so that 0.02675 is 2.68% where the float format gave
    2.67%; `signed` puts a plus before a gain."""
    rounded = (as_decimal(value) * 100).quantize(CENT, rounding=ROUND_HALF_UP)
    return f"{'+' if signed and rounded >= 0 else ''}{rounded}%"


def as_stated(value: Union[Decimal, float], percent: bool = False,
              grouped: bool = False) -> str:
    """A stated figure as it was stated, its own digits and no rounding:
    0.125 as a percent is 12.5%, where the whole-percent format printed
    12%; 2.50 is 2.5. `percent` reads a share and prints it per hundred;
    `grouped` puts the thousands commas in, as a holding's shares print,
    8.6 and not the 9 a whole-number format gave."""
    figure = as_decimal(value) * (100 if percent else 1)
    text = format(figure.normalize(), ",f" if grouped else "f")
    return f"{text}%" if percent else text


def as_decimal(value: Union[Decimal, float]) -> Decimal:
    """The decimal a figure prints as; a float, NumPy's or an int among
    them, is read as the float it is, and a decimal is returned as it is.
    Raises on what is no finite number: None, a string, NaN or infinity."""
    if isinstance(value, str):
        raise TypeError(f"{value!r} is text, not a figure.")
    figure = value if isinstance(value, Decimal) else Decimal(repr(float(value)))
    if not figure.is_finite():
        raise ValueError(f"{value!r} is not a finite figure.")
    return figure
