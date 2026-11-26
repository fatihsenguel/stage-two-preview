"""
A return over a window: the portfolio's holdings between two days, with the
buys and sells inside them.

Pure arithmetic over ledger rows, closes and rates. No database, no LLM, no
state. The tool that calls it reads the rows, the closes and the rates and
prints the result; this module only computes.

Reference: tests/golden/expected_values.md Part 22, and decisions D69-D74;
for the index the portfolio is judged against, Part 24 and D77-D81
(`against_index`); for each holding's own move, Part 27 and D91-D94, and
across its own trades, Part 28 and D95-D100.

  D69  A time-weighted return over the holdings. The window is cut at each
       date with a trade on it; each piece is the holdings' value at its
       end, less the money put in on that date, over the value at its
       start; the pieces are multiplied and 1 taken away. Cash is not in it,
       having no history; dividends are not in this, the price return, and
       are in the total return beside it (Part 51). Each return is simple,
       on closes as traded (D19).
  D70  Calendar days, both ends included. The opening value is at each
       holding's last close on or before the day before the first day, and
       no more than six days before it; the closing value at the last close
       on or before the last day, within the six days before it (D62).
       "month" and "year" are the first day of the day asked's month and
       year, "today" the day asked.
  D71  A trade at the close of its date; the money put in is the date's
       buys' `amount` less its sales' `amount` (D11, D14).
  D72  A holding in another currency at its close times the rate on that
       close's date (D16); a missing rate raises (D17).
  D74  What cannot be computed raises, naming why; no shorter window is put
       in its place.
  D91  Each holding held at the opening or the closing, or traded inside
       the window, is named; one held at neither end and never traded
       inside is not.
  D92  Its move in its own currency is its closing close over its opening
       close, less 1; in the portfolio's currency, each close times its rate;
       its gain, its quantity times the difference of the two, in the
       portfolio's currency. The closes and rates are the portfolio's own.
  D96  A holding with a trade of its own inside the window is chained as
       D69 chains the portfolio, cut at its own trade dates, the money put
       into it its buys' `amount` less its sales'.
  D97  A piece that starts with nothing held of it starts from the money
       paid: its value at the purchase date's close over the amount.
  D98  Its gain is its closing value less its opening value less the money
       put in plus the money taken out; the gains add to the portfolio's.
  D99  A traded holding in another currency has no move in its own
       currency: a trade's money is in the portfolio's.

Each holding's contribution (Part 49): its gain on each day with a close,
less the money put into it that day, over the portfolio's value at the
previous close; the days' contributions add to the day's return, the
window's are their sum, and the residual against the chained return is
stated. A close the day lacks leaves the return and states the gap.

With dividends (Part 51): each per-share dividend whose ex-date falls in
the window, times the quantity held at the close before it, in the
portfolio's currency at the rate of the holding's close for the ex-date;
the total return chains Part 22's pieces cut also at those ex-dates, the
dividend counted as money taken out. The price return is unchanged. A
held ticker whose dividends were not read, or a missing rate, leaves the
total return uncomputed, naming why; the price return stands.

The policy's index by day (Part 52, `index_by_day`): on each of the
contributions' days, the index's last close on or before it, at its date's
rate, over the previous day's; the difference, the portfolio's day return
less it. Another index a question names is compared as Part 24 compares
the policy's (`against_index`).

No rounding anywhere: the formatter rounds once, at printing (D73).
"""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

__all__ = ["SLACK_DAYS", "START_WORDS", "END_WORDS", "HoldingMove", "IndexComparison", "IndexDay",
           "Contributions", "DividendReceived",
           "WindowReturn",
           "WindowReturnError", "against_index", "index_by_day", "window", "window_return"]

# D62's six calendar days before the day a close is asked for.
SLACK_DAYS = 6
# "last month" is the previous calendar month, its first day as a window's
# first and its last day as a window's last (my word, 10 October 2026).
LAST_MONTH = "last month"
# "week" is the 7 days ending on the day asked, both included, the span the
# news reads for "this week" (my word, 10 October 2026, after scenario F's
# first run sent a calendar week to the news and was refused).
WEEK_DAYS = 7
START_WORDS = ("week", "month", "year", LAST_MONTH)
END_WORDS = ("today", LAST_MONTH)


class WindowReturnError(Exception):
    """Raised when a return over the window cannot be computed correctly."""


@dataclass(frozen=True)
class HoldingMove:
    """One holding over the window (D91, D92); a traded one chained across
    its own trades (D96 to D99), with no move in its own currency where
    that is not the portfolio's."""
    ticker: str
    traded: bool
    currency: str
    sold_whole: bool = False
    quantity: Optional[Decimal] = None
    opening_date: Optional[dt.date] = None
    closing_date: Optional[dt.date] = None
    opening_close: Optional[Decimal] = None
    closing_close: Optional[Decimal] = None
    move_own: Optional[Decimal] = None
    move: Optional[Decimal] = None
    gain: Optional[Decimal] = None


@dataclass(frozen=True)
class Contributions:
    """Each holding's contribution to the window's return (Part 49): by
    day, its gain on the day over the portfolio's value at the previous
    day's close; over the window, the sum of its days. The days' returns
    chain to the window's return; their sum differs from it by the
    residual, stated and spread over no holding. `gap` says why no
    contribution was computed, the return standing without it."""
    days: Tuple[dt.date, ...] = ()
    by_day: Tuple[Tuple[dt.date, Tuple[Tuple[str, Decimal], ...], Decimal], ...] = ()
    window: Tuple[Tuple[str, Decimal], ...] = ()
    total: Optional[Decimal] = None
    residual: Optional[Decimal] = None
    gap: Optional[str] = None


@dataclass(frozen=True)
class DividendReceived:
    """One dividend the portfolio received in the window (Part 51): its
    per-share amount in the holding's currency, the quantity held at the
    close before the ex-date, the rate of the close it is valued at, and
    the amount in the portfolio's currency."""
    ticker: str
    ex_date: dt.date
    per_share: Decimal
    quantity: Decimal
    rate: Decimal
    amount: Decimal


@dataclass(frozen=True)
class WindowReturn:
    first: dt.date
    last: dt.date
    opening_dates: Tuple[dt.date, ...]
    closing_dates: Tuple[dt.date, ...]
    opening_value: Decimal
    closing_value: Decimal
    put_in: Decimal
    taken_out: Decimal
    gain: Decimal
    ret: Decimal
    trades: int
    trade_dates: Tuple[dt.date, ...]
    currency: str
    converted: bool
    holdings: Tuple[HoldingMove, ...] = ()
    contributions: Optional[Contributions] = None
    total_ret: Optional[Decimal] = None
    total_gain: Optional[Decimal] = None
    dividends_received: Decimal = Decimal(0)
    dividend_rows: Tuple[DividendReceived, ...] = ()
    dividend_gap: Optional[str] = None


def _day(text: str, words: Sequence[str], today: dt.date, which: str) -> dt.date:
    if text in words:
        if text == "week":
            return today - dt.timedelta(days=WEEK_DAYS - 1)
        if text == "month":
            return today.replace(day=1)
        if text == "year":
            return today.replace(month=1, day=1)
        if text == LAST_MONTH:
            last_day = today.replace(day=1) - dt.timedelta(days=1)
            return last_day.replace(day=1) if which == "first day" else last_day
        return today
    try:
        if len(text) != 10:
            raise ValueError(text)
        return dt.date.fromisoformat(text)
    except ValueError:
        named = " or ".join(f'"{w}"' for w in words)
        raise WindowReturnError(f"the {which} {text!r} is neither a date written YYYY-MM-DD "
                                f"nor {named}.") from None


def window(start: str, end: str, today: dt.date) -> Tuple[dt.date, dt.date]:
    """The window's first and last day (D70): each a date, or for the first
    "week", "month" or "year" and for the last "today", or for either "last month",
    the previous calendar month's first or last day, read on the day
    asked."""
    first = _day(start, START_WORDS, today, "first day")
    last = _day(end, END_WORDS, today, "last day")
    if last > today:
        raise WindowReturnError(f"the last day {last} is after the day asked, {today}.")
    if first > last:
        raise WindowReturnError(f"the first day {first} is after the last, {last}.")
    return first, last


def _date(value) -> dt.date:
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _close_on(series: Sequence[Tuple[dt.date, Decimal]], name: str,
              day: dt.date) -> Tuple[dt.date, Decimal]:
    """The last close of `series` dated on or before `day`, within the six
    days before it (D70, D78)."""
    earliest = day - dt.timedelta(days=SLACK_DAYS)
    found = [(d, c) for d, c in series if earliest <= d <= day]
    if not found:
        raise WindowReturnError(
            f"{name} has no close from {earliest} to {day}; a value on {day} needs one in the "
            "six days before it.")
    return found[-1]


def window_return(rows: Sequence[Mapping], first: dt.date, last: dt.date,
                  closes: Mapping[str, Sequence[Tuple[dt.date, Decimal]]], *,
                  base_currency: str, currencies: Mapping[str, str],
                  rates: Mapping[str, Mapping[dt.date, Decimal]],
                  dividends: Optional[Mapping[str, Sequence[Tuple[dt.date, Decimal]]]] = None
                  ) -> WindowReturn:
    """
    The holdings' time-weighted return from `first` to `last` (D69 to D72),
    and with `dividends` the total return (Part 51).

    Args:
        rows: one portfolio's ledger rows, each its date, type ('buy' or
              'sell'), ticker, quantity and amount in the base currency
        first, last: the window's first and last day, both included
        closes: each ticker's (date, close) pairs, in its currency
        base_currency: the portfolio's currency (D15)
        currencies: each ticker's currency
        rates: {currency: {date: base units per one unit}}
        dividends: each ticker's (ex-date, per-share amount) pairs in its
              currency, as read; a ticker absent was not read. None: none
              read, and the total return is a gap.

    Raises:
        WindowReturnError naming why: an empty ledger, a first day on or
        before the first purchase, a window no close falls inside, a holding
        with no close in the six days a value needs, a foreign holding with
        no rate on its close's date, a piece that starts with nothing held.
    """
    if not rows:
        raise WindowReturnError("the portfolio has no ledger rows: nothing to measure.")
    ordered = sorted(rows, key=lambda r: _date(r["date"]))
    buys = [_date(r["date"]) for r in ordered if r["type"] == "buy"]
    if not buys:
        raise WindowReturnError("the portfolio's ledger has no purchase.")
    if first <= buys[0]:
        raise WindowReturnError(
            f"the first day {first} is on or before the portfolio's first purchase, "
            f"{buys[0]}: nothing was held before it. A window from {buys[0] + dt.timedelta(1)} "
            "can be measured.")

    series = {t: sorted((_date(d), Decimal(c)) for d, c in pairs)
              for t, pairs in closes.items()}

    def held_after(day: dt.date) -> Dict[str, Decimal]:
        quantity: Dict[str, Decimal] = {}
        for r in ordered:
            if _date(r["date"]) > day:
                break
            q = Decimal(str(r["quantity"]))
            quantity[r["ticker"]] = quantity.get(r["ticker"], Decimal(0)) + (
                q if r["type"] == "buy" else -q)
        return {t: q for t, q in quantity.items() if q > 0}

    converted = False

    def priced(ticker: str, day: dt.date) -> Tuple[dt.date, Decimal, Decimal]:
        """The holding's close for `day`, its date, and its rate on that date."""
        nonlocal converted
        on, close = _close_on(series.get(ticker, ()), ticker, day)
        currency = currencies.get(ticker)
        if not currency:
            raise WindowReturnError(f"{ticker} states no currency; its close cannot be "
                                    f"valued in {base_currency}.")
        rate = Decimal(1)
        if currency != base_currency:
            found = (rates.get(currency) or {}).get(on)
            if found is None:
                raise WindowReturnError(
                    f"{ticker} has no {base_currency}/{currency} rate on {on}, its close's "
                    "date; nothing falls back to another day's rate or to 1 (D17).")
            rate, converted = Decimal(str(found)), True
        return on, close, rate

    def value(day: dt.date) -> Tuple[Decimal, List[dt.date]]:
        total, dated = Decimal(0), []
        for ticker, quantity in sorted(held_after(day).items()):
            on, close, rate = priced(ticker, day)
            total += quantity * close * rate
            dated.append(on)
        return total, dated

    tickers = {r["ticker"] for r in ordered}
    if not any(first <= d <= last for t in tickers for d, _ in series.get(t, ())):
        raise WindowReturnError(f"no close falls inside the window {first} to {last}.")

    opening_day = first - dt.timedelta(days=1)
    opening_value, opening_dates = value(opening_day)
    inside = [r for r in ordered if first <= _date(r["date"]) <= last]
    trade_dates = sorted({_date(r["date"]) for r in inside})

    growth, start_value, start_day = Decimal(1), opening_value, opening_day
    put_in = taken_out = Decimal(0)
    for day in trade_dates:
        if start_value == 0:
            raise WindowReturnError(
                f"nothing is held after {start_day}'s trades, so the piece from that date has "
                "no start value.")
        on_day = [r for r in inside if _date(r["date"]) == day]
        bought = sum((Decimal(str(r["amount"])) for r in on_day if r["type"] == "buy"),
                     Decimal(0))
        sold = sum((Decimal(str(r["amount"])) for r in on_day if r["type"] == "sell"),
                   Decimal(0))
        end_value, _ = value(day)
        growth *= (end_value - (bought - sold)) / start_value
        put_in, taken_out = put_in + bought, taken_out + sold
        start_value, start_day = end_value, day

    closing_value, closing_dates = value(last)
    if start_value != 0:
        growth *= closing_value / start_value
    elif closing_value != 0:
        raise WindowReturnError(
            f"nothing is held after {start_day}'s trades, so the piece from that date has no "
            "start value.")

    opening_held, closing_held = held_after(opening_day), held_after(last)
    traded = {r["ticker"] for r in inside}
    holdings = []
    for ticker in sorted(set(opening_held) | set(closing_held) | traded):
        currency = currencies.get(ticker) or ""
        if ticker in traded:
            holdings.append(_traded_move(ticker, currency, opening_day, last,
                                         [r for r in inside if r["ticker"] == ticker],
                                         opening_held.get(ticker, Decimal(0)),
                                         held_after, priced, base_currency))
            continue
        quantity = opening_held[ticker]
        opened_on, opened, opened_rate = priced(ticker, opening_day)
        closed_on, closed, closed_rate = priced(ticker, last)
        holdings.append(HoldingMove(
            ticker=ticker, traded=False, currency=currency, quantity=quantity,
            opening_date=opened_on, closing_date=closed_on,
            opening_close=opened, closing_close=closed,
            move_own=closed / opened - 1,
            move=(closed * closed_rate) / (opened * opened_rate) - 1,
            gain=quantity * (closed * closed_rate - opened * opened_rate)))

    ret = growth - 1
    names = sorted(set(opening_held) | set(closing_held) | traded)
    try:
        total_ret, received = _with_dividends(
            dividends, names, first, last, opening_day, opening_value, inside, held_after,
            value, priced)
        dividend_gap = None
    except WindowReturnError as error:
        total_ret, received, dividend_gap = None, (), f"no total return is computed: {error}"
    try:
        contributions = _contributions(first, last, opening_day, inside, series, tickers,
                                       held_after, priced, ret)
    except WindowReturnError as error:
        contributions = Contributions(gap=f"no contribution is computed: {error}")

    return WindowReturn(
        first=first, last=last,
        opening_dates=tuple(sorted(set(opening_dates))),
        closing_dates=tuple(sorted(set(closing_dates))),
        opening_value=opening_value, closing_value=closing_value,
        put_in=put_in, taken_out=taken_out,
        gain=closing_value - opening_value - put_in + taken_out,
        ret=ret, trades=len(inside), trade_dates=tuple(trade_dates),
        currency=base_currency, converted=converted, holdings=tuple(holdings),
        contributions=contributions,
        total_ret=total_ret,
        total_gain=(None if total_ret is None else
                    closing_value - opening_value - put_in + taken_out
                    + sum((d.amount for d in received), Decimal(0))),
        dividends_received=sum((d.amount for d in received), Decimal(0)),
        dividend_rows=tuple(received), dividend_gap=dividend_gap)


def _with_dividends(dividends, names, first, last, opening_day, opening_value, inside,
                    held_after, value, priced) -> Tuple[Decimal, List[DividendReceived]]:
    """Part 51: the dividends received in the window, and the total return,
    Part 22's chain cut also at each ex-date with a dividend received, the
    dividend counted as money taken out at its cut."""
    if dividends is None:
        raise WindowReturnError("no dividends were read")
    unread = [t for t in names if t not in dividends]
    if unread:
        raise WindowReturnError("no dividends were read for " + ", ".join(unread) + ".")
    received: List[DividendReceived] = []
    for ticker in names:
        for ex_date, per_share in sorted((_date(d), Decimal(str(a)))
                                         for d, a in dividends[ticker]):
            if not first <= ex_date <= last:
                continue
            quantity = held_after(ex_date - dt.timedelta(days=1)).get(ticker, Decimal(0))
            if quantity == 0:
                continue
            _, _, rate = priced(ticker, ex_date)
            received.append(DividendReceived(ticker=ticker, ex_date=ex_date,
                                             per_share=per_share, quantity=quantity,
                                             rate=rate, amount=quantity * per_share * rate))
    received.sort(key=lambda d: (d.ex_date, d.ticker))

    cuts = sorted({_date(r["date"]) for r in inside} | {d.ex_date for d in received})
    growth, start_value, start_day = Decimal(1), opening_value, opening_day
    for day in cuts:
        if start_value == 0:
            raise WindowReturnError(
                f"nothing is held after {start_day}'s trades, so the piece from that date "
                "has no start value.")
        flow = Decimal(0)
        for r in inside:
            if _date(r["date"]) == day:
                amount = Decimal(str(r["amount"]))
                flow += amount if r["type"] == "buy" else -amount
        paid = sum((d.amount for d in received if d.ex_date == day), Decimal(0))
        end_value, _ = value(day)
        growth *= (end_value - flow + paid) / start_value
        start_value, start_day = end_value, day
    closing_value, _ = value(last)
    if start_value != 0:
        growth *= closing_value / start_value
    return growth - 1, received


def _contributions(first, last, opening_day, inside, series, tickers, held_after, priced,
                   ret) -> Contributions:
    """Part 49: each holding's gain on each day of the window with a close,
    the money put into it that day taken off, over the portfolio's value at
    the previous day's close."""
    days = sorted({d for t in tickers for d, _ in series.get(t, ()) if first <= d <= last})

    def worth(day: dt.date) -> Dict[str, Decimal]:
        out = {}
        for ticker, quantity in held_after(day).items():
            _, close, rate = priced(ticker, day)
            out[ticker] = quantity * close * rate
        return out

    before = worth(opening_day)
    sums: Dict[str, Decimal] = {}
    by_day = []
    previous = opening_day
    for day in days:
        total = sum(before.values(), Decimal(0))
        if total == 0:
            raise WindowReturnError(f"nothing is held at the close before {day}, so no "
                                    "weight is formed for it")
        now = worth(day)
        flows: Dict[str, Decimal] = {}
        # A trade dated on a day without a close (a weekend, a holiday of
        # every exchange held) counts on the next day with one.
        for r in inside:
            if previous < _date(r["date"]) <= day:
                amount = Decimal(str(r["amount"]))
                flows[r["ticker"]] = flows.get(r["ticker"], Decimal(0)) + (
                    amount if r["type"] == "buy" else -amount)
        shares = []
        for ticker in sorted(set(before) | set(now) | set(flows)):
            gain = (now.get(ticker, Decimal(0)) - before.get(ticker, Decimal(0))
                    - flows.get(ticker, Decimal(0)))
            share = gain / total
            shares.append((ticker, share))
            sums[ticker] = sums.get(ticker, Decimal(0)) + share
        by_day.append((day, tuple(shares), sum((c for _, c in shares), Decimal(0))))
        before, previous = now, day
    window = tuple(sorted(sums.items()))
    added = sum((c for _, c in window), Decimal(0))
    return Contributions(days=tuple(days), by_day=tuple(by_day), window=window, total=added,
                         residual=ret - added)


def _traded_move(ticker, currency, opening_day, last, own, opening_quantity, held_after,
                 priced, base_currency) -> HoldingMove:
    """One holding with a trade of its own inside the window, chained across
    its own trade dates (D96); a piece that starts with nothing held of it
    starts from the money paid (D97); its gain as D98 states."""

    def worth(day: dt.date) -> Decimal:
        quantity = held_after(day).get(ticker, Decimal(0))
        if quantity == 0:
            return Decimal(0)
        _, close, rate = priced(ticker, day)
        return quantity * close * rate

    opening = Decimal(0)
    if opening_quantity:
        _, close, rate = priced(ticker, opening_day)
        opening = opening_quantity * close * rate
    growth, start = Decimal(1), opening
    put_in = taken_out = Decimal(0)
    for day in sorted({_date(r["date"]) for r in own}):
        on_day = [r for r in own if _date(r["date"]) == day]
        bought = sum((Decimal(str(r["amount"])) for r in on_day if r["type"] == "buy"),
                     Decimal(0))
        sold = sum((Decimal(str(r["amount"])) for r in on_day if r["type"] == "sell"),
                   Decimal(0))
        end = worth(day)
        growth *= (end + sold) / bought if start == 0 else (end - (bought - sold)) / start
        put_in, taken_out, start = put_in + bought, taken_out + sold, end
    closing = worth(last)
    if start != 0:
        growth *= closing / start
    move = growth - 1
    return HoldingMove(
        ticker=ticker, traded=True, currency=currency, sold_whole=closing == 0,
        move=move, move_own=move if currency == base_currency else None,
        gain=closing - opening - put_in + taken_out)


@dataclass(frozen=True)
class IndexComparison:
    index: str
    opening_date: dt.date
    closing_date: dt.date
    opening_close: Decimal
    closing_close: Decimal
    ret: Decimal
    ret_own: Decimal
    difference: Decimal
    currency: str
    converted: bool


def against_index(first: dt.date, last: dt.date, portfolio_return: Decimal,
                  closes: Sequence[Tuple[dt.date, Decimal]], *, index: str,
                  base_currency: str, currency: str,
                  rates: Mapping[str, Mapping[dt.date, Decimal]]) -> IndexComparison:
    """
    The index's return over the portfolio's window, and the portfolio's
    return less it (expected_values.md Part 24, D77 to D81).

    The index is valued at its last close on or before the day before
    `first` and on or before `last`, each within the six days before it, as
    a holding is (D78); nothing is traded in it, so its return is the
    closing value over the opening value, less 1. In `base_currency`, each
    close times the rate on its own date (D79); the return in the index's
    own `currency` beside it. The difference is of the unrounded returns
    (D80).

    Raises:
        WindowReturnError naming why: no close of the index in the six days
        the opening or the closing needs, no rate on an index close's date.
    """
    series = sorted((_date(d), Decimal(c)) for d, c in closes)
    opening_date, opening_close = _close_on(series, index, first - dt.timedelta(days=1))
    closing_date, closing_close = _close_on(series, index, last)
    ret_own = closing_close / opening_close - 1
    ret, converted = ret_own, False
    if currency != base_currency:
        found = rates.get(currency) or {}
        for on in (opening_date, closing_date):
            if found.get(on) is None:
                raise WindowReturnError(
                    f"{index} has no {base_currency}/{currency} rate on {on}, its close's "
                    "date; nothing falls back to another day's rate or to 1 (D17).")
        ret = (closing_close * Decimal(str(found[closing_date]))) / (
            opening_close * Decimal(str(found[opening_date]))) - 1
        converted = True
    return IndexComparison(
        index=index, opening_date=opening_date, closing_date=closing_date,
        opening_close=opening_close, closing_close=closing_close, ret=ret, ret_own=ret_own,
        difference=portfolio_return - ret, currency=base_currency, converted=converted)


@dataclass(frozen=True)
class IndexDay:
    """One day of the benchmark by day (Part 52): the index's close used,
    its day return, the portfolio's day return (Part 49) and the
    difference, the portfolio's less the index's."""
    day: dt.date
    close_date: dt.date
    index_ret: Decimal
    portfolio_ret: Decimal
    difference: Decimal


def index_by_day(by_day: Sequence[Tuple[dt.date, object, Decimal]], opening_day: dt.date,
                 closes: Sequence[Tuple[dt.date, Decimal]], *, index: str,
                 base_currency: str, currency: str,
                 rates: Mapping[str, Mapping[dt.date, Decimal]]) -> Tuple[IndexDay, ...]:
    """
    The index's return on each of the portfolio's days beside the
    portfolio's (expected_values.md Part 52): its value on a day is its
    last close on or before it, within six days (D78), times the rate on
    that close's date (D79); the first day's previous value is at the
    window's opening. A day the index did not close carries its previous
    close, a day return of 0.

    Args:
        by_day: Part 49's (day, contributions, day's return) rows
        opening_day: the day before the window's first

    Raises:
        WindowReturnError naming why: no close in the six days a value
        needs, no rate on a close's date.
    """
    series = sorted((_date(d), Decimal(c)) for d, c in closes)
    found = rates.get(currency) or {}

    def valued(on_or_before: dt.date) -> Tuple[dt.date, Decimal]:
        on, close = _close_on(series, index, on_or_before)
        if currency == base_currency:
            return on, close
        rate = found.get(on)
        if rate is None:
            raise WindowReturnError(
                f"{index} has no {base_currency}/{currency} rate on {on}, its close's date; "
                "nothing falls back to another day's rate or to 1 (D17).")
        return on, close * Decimal(str(rate))

    _, before = valued(opening_day)
    out = []
    for d, _, portfolio in by_day:
        on, now = valued(d)
        ret = now / before - 1
        out.append(IndexDay(day=d, close_date=on, index_ret=ret, portfolio_ret=portfolio,
                            difference=portfolio - ret))
        before = now
    return tuple(out)
