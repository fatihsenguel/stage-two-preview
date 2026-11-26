"""
Each holding's contribution to a window's return, checked against
tests/golden/expected_values.md Part 49, computed by hand as fractions
before the code (decision 147, W2). Pure: ledger rows and closes in.
"""

import datetime as dt
from decimal import Decimal as D
from fractions import Fraction as F

from portfolio_tool.quant import window_return as wr
from portfolio_tool.rounding import to_percent


def day(text):
    return dt.date.fromisoformat(text)


def row(date, type_, ticker, quantity, amount):
    return {"date": day(date), "type": type_, "ticker": ticker, "quantity": quantity,
            "amount": amount}


BOUGHT = [row("2026-01-02", "buy", "A", 10, 1000), row("2026-01-02", "buy", "B", 20, 1000)]
CLOSES = {"A": [(day("2026-01-02"), D("100")), (day("2026-01-05"), D("110")),
                (day("2026-01-06"), D("99")), (day("2026-01-07"), D("108.9"))],
          "B": [(day("2026-01-02"), D("50")), (day("2026-01-05"), D("50")),
                (day("2026-01-06"), D("55")), (day("2026-01-07"), D("55"))]}


def measured(rows):
    return wr.window_return(rows, day("2026-01-05"), day("2026-01-07"), CLOSES,
                            base_currency="EUR", currencies={"A": "EUR", "B": "EUR"}, rates={})


def near(value, fraction):
    return abs(F(str(value)) - fraction) < F(1, 10 ** 20)


def test_a_no_trade_inside():
    got = measured(BOUGHT)
    c = got.contributions
    assert c.gap is None and c.days == (day("2026-01-05"), day("2026-01-06"), day("2026-01-07"))
    assert [(d, dict(s)) for d, s, _ in c.by_day][0] == (day("2026-01-05"),
                                                        {"A": D("0.05"), "B": D(0)})
    a, b = dict(c.window)["A"], dict(c.window)["B"]
    assert near(a, F(359, 7980)) and near(b, F(1, 21))
    assert near(c.total, F(359, 7980) + F(1, 21))
    assert got.ret == D("0.0945")
    assert near(c.residual, F(189, 2000) - F(359, 7980) - F(1, 21))
    assert [to_percent(x) for x in (a, b, c.total, got.ret, c.residual)] == [
        "4.50%", "4.76%", "9.26%", "9.45%", "0.19%"]
    # Each day's contributions add to its return; the days chain to the window's.
    growth = D(1)
    for _, shares, r in c.by_day:
        assert r == sum(x for _, x in shares)
        growth *= 1 + r
    assert near(growth - 1, F(189, 2000))


def test_b_a_purchase_inside():
    rows = BOUGHT + [row("2026-01-06", "buy", "A", 5, 500)]
    got = measured(rows)
    c = got.contributions
    a, b = dict(c.window)["A"], dict(c.window)["B"]
    expected_a = F(1, 20) - F(115, 2100) + F(1485, 25850)
    expected_r = F(2085, 2000) * F(27335, 25850) - 1
    assert near(a, expected_a) and near(b, F(100, 2100))
    assert near(got.ret, expected_r) and near(c.residual, expected_r - expected_a - F(1, 21))
    assert [to_percent(x) for x in (a, b, c.total, got.ret, c.residual)] == [
        "5.27%", "4.76%", "10.03%", "10.24%", "0.21%"]
    # A's daily gains add to its gain over the window (D98).
    assert dict((h.ticker, h.gain) for h in got.holdings)["A"] == D("133.5")
    assert dict(c.by_day[1][1])["A"] == D(-115) / D(2100)


def test_a_holding_without_a_close_that_day_counts_its_last():
    closes = dict(CLOSES)
    closes["B"] = [(day("2026-01-02"), D("50")), (day("2026-01-07"), D("55"))]
    got = measured_with(closes, day("2026-01-07"))
    c = got.contributions
    assert c.gap is None
    # B stands at 50 through 01-06: the total before 01-07 is 990 + 1000.
    assert dict(c.by_day[2][1])["B"] == D(100) / D(1990)


def test_a_close_older_than_six_days_is_a_gap_and_the_return_stands():
    closes = {"A": CLOSES["A"] + [(day(f"2026-01-{n:02d}"), D("108.9")) for n in range(8, 15)],
              "B": [(day("2026-01-02"), D("50")), (day("2026-01-14"), D("55"))]}
    got = measured_with(closes, day("2026-01-14"))
    assert got.ret == D("0.0945")
    assert got.contributions.gap.startswith("no contribution is computed: B has no close")


def measured_with(closes, last):
    return wr.window_return(BOUGHT, day("2026-01-05"), last, closes, base_currency="EUR",
                            currencies={"A": "EUR", "B": "EUR"}, rates={})



def test_a_purchase_dated_on_a_day_without_a_close():
    """No close on 2026-01-06 for either holding, and A bought that day (5
    for 500): the money is taken off on the next day with a close. On
    2026-01-07, A: (15 x 108.9 - 10 x 110 - 500) / 2100 = 33.5 / 2100,
    B: (20 x 55 - 20 x 50) / 2100 = 100 / 2100 (milestone review R1;
    without it A's day read 533.5 / 2100)."""
    closes = {t: [(d, c) for d, c in rows if d != day("2026-01-06")]
              for t, rows in CLOSES.items()}
    rows = BOUGHT + [row("2026-01-06", "buy", "A", 5, 500)]
    got = wr.window_return(rows, day("2026-01-05"), day("2026-01-07"), closes,
                           base_currency="EUR", currencies={"A": "EUR", "B": "EUR"}, rates={})
    c = got.contributions
    assert c.days == (day("2026-01-05"), day("2026-01-07"))
    last = dict(c.by_day[1][1])
    assert near(last["A"], F(335, 21000)) and near(last["B"], F(100, 2100))
    assert near(dict(c.window)["A"], F(1, 20) + F(335, 21000))
