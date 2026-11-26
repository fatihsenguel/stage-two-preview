## Part 49 — Each holding's contribution to the window's return (`window_return`)

Written by hand on 24 November 2026, before the code (decision 147,
`docs/fast-track.md` W2). The ledger and closes are made up; every value
below is computed by hand, as fractions, before any code.

### Rules

- The days are the window's days on which any holding held or traded in
  it has a close; the day before is the window's opening (Part 22, D70).
- A holding's contribution on a day is its value at the day's close
  less its value at the previous day's close, less the money put into it
  that day (buys less sales, D71), over the portfolio's value at the
  previous day's close. Without a trade this is its previous-close weight
  times its return on the day.
- Added 25 November 2026 (R1's milestone review): the money of a trade
  dated on a day without a close is put in on the next day with one.
  No value changes.
- The day's contributions add to the day's return exactly. Chained, the
  days' returns give the window's time-weighted return (D69) exactly.
- A holding's window contribution is the sum of its daily ones. The sum
  over holdings is the sum of the daily returns, not their chain; the
  difference, the window's return less that sum, is the residual,
  stated, never spread over the holdings.
- Each holding's daily gains add to its gain over the window (D98).

### The ledger and closes (EUR, one currency)

Bought 2026-01-02: A 10 for 1000, B 20 for 1000. Window 2026-01-05 to
2026-01-07; the opening is 2026-01-02's close.

| Day | A close | B close |
|---|---|---|
| 2026-01-02 | 100 | 50 |
| 2026-01-05 | 110 | 50 |
| 2026-01-06 | 99 | 55 |
| 2026-01-07 | 108.9 | 55 |

### A. No trade inside

| Day | A value | B value | Total | A contribution | B contribution | Day's return |
|---|---|---|---|---|---|---|
| 01-05 | 1100 | 1000 | 2100 | 100 / 2000 = 0.05 | 0 | 0.05 |
| 01-06 | 990 | 1100 | 2090 | -110 / 2100 | 100 / 2100 | -10 / 2100 |
| 01-07 | 1089 | 1100 | 2189 | 99 / 2090 | 0 | 99 / 2090 |

Window: A 359/7980 = 0.044987... (4.50%), B 1/21 = 0.047619... (4.76%),
sum 0.092606... (9.26%); return 2189 / 2000 - 1 = 0.0945 (9.45%);
residual 0.001893... (0.19%). Gains A 89, B 100, sum 189 = 2189 - 2000.

### B. A purchase inside: 2026-01-06, A 5 more for 500

| Day | A value | B value | Total | A contribution | B contribution | Day's return |
|---|---|---|---|---|---|---|
| 01-05 | 1100 | 1000 | 2100 | 100 / 2000 | 0 | 0.05 |
| 01-06 | 15 x 99 = 1485 | 1100 | 2585 | (1485 - 1100 - 500) / 2100 = -115 / 2100 | 100 / 2100 | -15 / 2100 |
| 01-07 | 15 x 108.9 = 1633.5 | 1100 | 2733.5 | 148.5 / 2585 | 0 | 148.5 / 2585 |

Window: A 0.052684... (5.27%), B 0.047619... (4.76%), sum 0.100303...
(10.03%); return 1.05 x 2085/2100 x 2733.5/2585 - 1 = 0.102388...
(10.24%), equal to Part 22's chain cut at the trade; residual
0.002084... (0.21%). A's gain 100 - 115 + 148.5 = 133.5 = 1633.5 - 1000
- 500.

