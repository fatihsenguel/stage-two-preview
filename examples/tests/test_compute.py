"""
The general computation over named operands, held to expected_values.md
Part 46 (portfolio_tool/compute.py). Made-up operands; every expected value
is the Part's, computed by hand.
"""

from decimal import Decimal

import pytest

from portfolio_tool.compute import ComputeError, Operand, evaluate, parse_unit, said_unit, said_value


def op(name, value, unit="USD", tier="sourced"):
    return Operand(name=name, value=Decimal(str(value)), unit=unit, tier=tier, source="test")


def ops(*items):
    return {o.name: o for o in items}


@pytest.mark.parametrize("row, expression, operands, exact, unit, percent, said", [
    ("A1", "oi / rev", ops(op("oi", 30_000_000), op("rev", 120_000_000)),
     Decimal("0.25"), "pure", True, "25.00%"),
    ("A2", "ytd9 - ytd6", ops(op("ytd9", 300), op("ytd6", 190)),
     Decimal("110"), "USD", False, "110"),
    ("A3", "(q - p) / p", ops(op("q", 110), op("p", 100)),
     Decimal("0.1"), "pure", True, "10.00%"),
    ("A4", "q * 4", ops(op("q", 110)), Decimal("440"), "USD", False, "440"),
    ("A5", "price / eps", ops(op("price", 150, "USD/shares"), op("eps", 6, "USD/shares")),
     Decimal("25"), "pure", False, "25"),
    ("A6", "(ocf - capex) / (price * shares)",
     ops(op("ocf", 50), op("capex", 20), op("price", 100, "USD/shares"),
         op("shares", 10, "shares")),
     Decimal("0.03"), "pure", True, "3.00%"),
    ("A10", "-x", ops(op("x", 5)), Decimal("-5"), "USD", False, "-5"),
    ("A11", "cash / shares", ops(op("cash", 1000), op("shares", 40, "shares")),
     Decimal("25"), "USD/shares", False, "25"),
])
def test_values(row, expression, operands, exact, unit, percent, said):
    result = evaluate(expression, operands)
    assert result.value == exact, row
    assert said_unit(result.unit) == unit, row
    assert said_value(result.value, result.unit, percent) == said, row
    assert result.on_judgement == (), row


def test_a7_a8_exact_kept_said_rounded():
    third = evaluate("a / b", ops(op("a", 1, "pure"), op("b", 3, "pure")))
    assert str(third.value) == "0." + "3" * 34
    assert said_value(third.value, third.unit, True) == "33.33%"
    two = evaluate("a / b", ops(op("a", 2, "pure"), op("b", 3, "pure")))
    assert said_value(two.value, two.unit, False) == "0.6667"


def test_a9_half_to_even():
    result = evaluate("x", ops(op("x", "1234567.5")))
    assert result.value == Decimal("1234567.5")
    assert said_value(result.value, result.unit, False) == "1,234,568"


def test_a12_rests_on_judgement():
    result = evaluate("ni / eq * r",
                      ops(op("ni", 12), op("eq", 100), op("r", "0.5", "pure", "judgement")))
    assert result.value == Decimal("0.06")
    assert said_value(result.value, result.unit, False) == "0.06"
    assert result.on_judgement == ("r",)


@pytest.mark.parametrize("row, expression, operands, words", [
    ("B1", "rev + shares", ops(op("rev", 1), op("shares", 1, "shares")), "units differ"),
    ("B2", "rev * 0.09", ops(op("rev", 1)), "only whole numbers"),
    ("B3", "rev * 1001", ops(op("rev", 1)), "only whole numbers"),
    ("B4", "a / (b - b)", ops(op("a", 1), op("b", 2)), "division by zero"),
    ("B5", "a", ops(op("a", 1), op("b", 2)), "b is given and not used"),
    ("B6", "a + c", ops(op("a", 1)), "c is named in the expression and is no operand"),
    ("B7", "a ** 2", ops(op("a", 1)), "not admitted"),
    ("B8", "abs(a)", ops(op("a", 1)), "not admitted"),
    ("B10", "a + b", ops(op("a", 1, "USD/shares"), op("b", 1)), "units differ"),
    ("B11", "", ops(op("a", 1)), "empty"),
    ("B11", "a" + " + a" * 125, ops(op("a", 1)), "longer than 500"),
])
def test_refusals(row, expression, operands, words):
    with pytest.raises(ComputeError, match=words):
        evaluate(expression, operands)


def test_b9_tier_named():
    with pytest.raises(ComputeError, match="tier 'owner'"):
        op("a", 1, tier="owner")


def test_booleans_and_floats_are_no_constants():
    for expression in ("a * True", "a * 2.0"):
        with pytest.raises(ComputeError, match="only whole numbers"):
            evaluate(expression, ops(op("a", 1)))


def test_units_parsed_and_said():
    assert parse_unit("USD/shares") == (("USD", 1), ("shares", -1))
    assert parse_unit("pure") == parse_unit("1") == parse_unit("") == ()
    assert said_unit(parse_unit("USD*USD")) == "USD^2"
    assert said_unit(parse_unit("1/shares")) == "1/shares"
    with pytest.raises(ComputeError):
        parse_unit("USD/shares/day")
