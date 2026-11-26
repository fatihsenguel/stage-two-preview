"""
One general computation over named operands (docs/fast-track.md S3;
expected_values.md Part 46).

A model states the arithmetic it wants as an expression over names; each
name is an operand whose value a tool resolved from an earlier result (a
filed figure, a figure by its period, a close, an earlier computation) or a
constant stated with its origin. The model never types a figure it read:
it names where the figure is. This module evaluates the expression exactly,
in decimal, and carries the operands' units through it, so that a sum of
dollars and shares, or a percent of something that is not a ratio, is
refused rather than printed.

The expression admits names, `+ - * /`, a leading minus, parentheses and
whole numbers from 1 to 1000 (to annualise, to scale, to count days). Any
other number is refused: a figure is an operand, never a literal. Nothing
is rounded inside; the result is rounded only where it is said.

A unit is a product of base units with integer powers: "USD" is USD^1,
"USD/shares" is USD^1 shares^-1, "pure" and "1" are dimensionless. Adding
or subtracting needs equal units; multiplying and dividing combine them.
"""

import ast
from dataclasses import dataclass
from decimal import Decimal, DivisionByZero, InvalidOperation, localcontext
from typing import Dict, Mapping, Optional, Tuple

__all__ = ["ComputeError", "Operand", "Result", "MAX_CONSTANT", "TIERS", "evaluate",
           "parse_unit", "said_unit", "said_value"]

MAX_CONSTANT = 1000
# The tiers an operand may carry, each as the provenance rules name it.
TIERS = ("verified", "sourced", "computed", "judgement")

Unit = Tuple[Tuple[str, int], ...]   # sorted (base, power), no zero power


class ComputeError(ValueError):
    """Raised on an expression or operands that cannot be computed as asked."""


@dataclass(frozen=True)
class Operand:
    """One named input: its value, unit, tier and where it came from."""
    name: str
    value: Decimal
    unit: str
    tier: str
    source: str
    period: Optional[str] = None

    def __post_init__(self):
        if self.tier not in TIERS:
            raise ComputeError(f"operand {self.name}: tier {self.tier!r} is none of "
                               f"{', '.join(TIERS)}")
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise ComputeError(f"operand {self.name}: its value is not a finite decimal")
        parse_unit(self.unit)


@dataclass(frozen=True)
class Result:
    value: Decimal
    unit: Unit
    on_judgement: Tuple[str, ...]     # the operands of tier judgement it rests on
    names: Tuple[str, ...]            # the operands used, in order of first use


def parse_unit(text: str) -> Unit:
    """'USD' -> (('USD', 1),); 'USD/shares' -> (('USD', 1), ('shares', -1));
    'pure', '1' and '' -> ()."""
    text = (text or "").strip()
    if text in ("", "1", "pure"):
        return ()
    powers: Dict[str, int] = {}
    parts = text.split("/")
    if len(parts) > 2:
        raise ComputeError(f"unit {text!r}: at most one '/'")
    for sign, part in zip((1, -1), parts):
        for base in part.split("*"):
            base = base.strip()
            if not base or not all(c.isalnum() or c == "_" for c in base):
                raise ComputeError(f"unit {text!r}: {base!r} is not a unit name")
            if base in ("1", "pure"):
                continue
            powers[base] = powers.get(base, 0) + sign
    return tuple(sorted((b, p) for b, p in powers.items() if p))


def _combine(a: Unit, b: Unit, sign: int) -> Unit:
    powers = dict(a)
    for base, power in b:
        powers[base] = powers.get(base, 0) + sign * power
    return tuple(sorted((k, v) for k, v in powers.items() if v))


def said_unit(unit: Unit) -> str:
    """The unit as written: 'USD', 'USD/shares', 'USD^2', or 'pure'."""
    if not unit:
        return "pure"

    def side(items):
        return "*".join(b if p == 1 else f"{b}^{p}" for b, p in items)
    top = [(b, p) for b, p in unit if p > 0]
    bottom = [(b, -p) for b, p in unit if p < 0]
    if not bottom:
        return side(top)
    return f"{side(top) or '1'}/{side(bottom)}"


def said_value(value: Decimal, unit: Unit, as_percent: bool) -> str:
    """The result as it is printed: a percent to two places, an amount of
    1,000 or more to a whole number with separators, anything else to four
    significant places after the point. The exact value is kept apart."""
    if as_percent:
        return f"{(value * 100).quantize(Decimal('0.01')):,}%"
    if abs(value) >= 1000:
        return f"{value.quantize(Decimal('1')):,}"
    if value == 0:
        return "0"
    return f"{value.quantize(Decimal('0.0001')).normalize():f}"


_BINARY = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}


def evaluate(expression: str, operands: Mapping[str, Operand]) -> Result:
    """The expression's exact value and unit over the operands it names.
    Every operand given must be used, and every name used must be given."""
    if not expression or len(expression) > 500:
        raise ComputeError("the expression is empty or longer than 500 characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise ComputeError(f"the expression does not parse: {error.msg}") from None
    used: list = []

    def walk(node) -> Tuple[Decimal, Unit]:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Name):
            if node.id not in operands:
                raise ComputeError(f"{node.id} is named in the expression and is no operand")
            if node.id not in used:
                used.append(node.id)
            op = operands[node.id]
            return op.value, parse_unit(op.unit)
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= MAX_CONSTANT:
                raise ComputeError(
                    f"the number {v!r} is written into the expression; only whole numbers "
                    f"from 1 to {MAX_CONSTANT} may be, and a figure is passed as an operand "
                    "with its source")
            return Decimal(v), ()
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            value, unit = walk(node.operand)
            return -value, unit
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            (a, ua), (b, ub) = walk(node.left), walk(node.right)
            sign = _BINARY[type(node.op)]
            if sign in "+-":
                if ua != ub:
                    raise ComputeError(f"{sign} of {said_unit(ua)} and {said_unit(ub)}: the "
                                       "units differ")
                return (a + b if sign == "+" else a - b), ua
            if sign == "*":
                return a * b, _combine(ua, ub, 1)
            if b == 0:
                raise ComputeError("a division by zero")
            return a / b, _combine(ua, ub, -1)
        raise ComputeError(f"{type(node).__name__} is not admitted; only names, + - * /, a "
                           "leading minus, parentheses and whole numbers")

    with localcontext() as ctx:
        ctx.prec = 34
        try:
            value, unit = walk(tree)
        except (InvalidOperation, DivisionByZero) as error:
            raise ComputeError(f"the arithmetic failed: {error.__class__.__name__}") from None
    unused = [n for n in operands if n not in used]
    if unused:
        raise ComputeError(f"operand {', '.join(unused)} is given and not used in the "
                           "expression")
    judged = tuple(n for n in used if operands[n].tier == "judgement")
    return Result(value=value, unit=unit, on_judgement=judged, names=tuple(used))
