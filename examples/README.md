# Examples

Two modules copied unchanged from the private source, each with the hand-computed reference
it was built against and the tests that check it. They need only Python 3.10+ and pytest:

```bash
cd examples
python -m pytest tests
```

The project's rule for a verified calculation: the reference values are worked out by hand,
as exact fractions, before any code is written. The code is then tested against them, and a
disagreement is investigated, never fixed by changing the reference.

## Time-weighted return and contributions

- `portfolio_tool/quant/window_return.py`: a portfolio's return over a window of days, with
  the trades inside it. The window is cut at each trade date and the pieces are chained
  (time-weighted). Each holding's contribution is its gain on each day over the portfolio's
  value at the previous close; the daily contributions add exactly to the daily return, and
  the difference between their sum and the chained return is stated as the compounding
  residual instead of being spread over the holdings. Holdings in other currencies,
  dividends by ex-date and a benchmark index are covered too. Pure arithmetic in `Decimal`:
  no database, no model, no state.
- `references/part49_contributions.md`: the hand-computed reference: a window without
  trades and one with a purchase inside it.
- `tests/test_contributions.py`: the module checked against it as exact fractions, plus
  the edge cases: a holding with no close on a day, a close too old to use (a gap, not a
  number), a purchase dated on a day without a close.

## Arithmetic the model asks for but does not do

- `portfolio_tool/compute.py`: the model states an expression over named operands, such as
  `gross_profit / revenue`. Each name resolves to a figure a tool produced earlier, with its
  unit, tier and source. The module evaluates the expression exactly, carries units through
  it (adding dollars to shares is refused), and refuses any literal number other than a
  small whole constant: a figure is always an operand with a source, never typed in.
- `references/part46_compute.md`: the hand-computed reference and the refusal cases.
- `tests/test_compute.py`: the tests.

`portfolio_tool/rounding.py` is included because the tests print percentages through it.
