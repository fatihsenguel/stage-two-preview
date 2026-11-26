## Part 46 — One general computation over named operands (`compute`)

Written by hand on 24 November 2026, before `portfolio_tool/compute.py`'s
tests (decision 147, `docs/fast-track.md` S3). The operands are made up.
Every value below is computed by hand; the code is held to them.

### A. Values

| # | Expression | Operands (value, unit) | Exact result | Unit | Said |
|---|---|---|---|---|---|
| A1 | `oi / rev`, as percent | oi 30,000,000 USD; rev 120,000,000 USD | 0.25 | pure | `25.00%` |
| A2 | `ytd9 - ytd6` | ytd9 300 USD; ytd6 190 USD | 110 | USD | `110` |
| A3 | `(q - p) / p`, as percent | q 110 USD; p 100 USD | 0.1 | pure | `10.00%` |
| A4 | `q * 4` | q 110 USD | 440 | USD | `440` |
| A5 | `price / eps` | price 150 USD/shares; eps 6 USD/shares | 25 | pure | `25` |
| A6 | `(ocf - capex) / (price * shares)`, as percent | ocf 50 USD; capex 20 USD; price 100 USD/shares; shares 10 shares | 0.03 | pure | `3.00%` |
| A7 | `a / b` | a 2 pure; b 3 pure | 0.666... (34 digits) | pure | `0.6667` |
| A8 | `a / b`, as percent | a 1 pure; b 3 pure | 0.333... | pure | `33.33%` |
| A9 | `x` | x 1,234,567.5 USD | 1234567.5 | USD | `1,234,568` (half to even) |
| A10 | `-x` | x 5 USD | -5 | USD | `-5` |
| A11 | `cash / shares` | cash 1,000 USD; shares 40 shares | 25 | USD/shares | `25` |
| A12 | `ni / eq * r` with r of tier judgement | ni 12 USD; eq 100 USD; r 0.5 pure | 0.06 | pure | `0.06`; rests on judgement: r |

### B. Refusals

| # | Asked | Refused because |
|---|---|---|
| B1 | `rev + shares`, rev USD, shares shares | the units differ |
| B2 | `rev * 0.09` | a literal that is not a whole number from 1 to 1000 |
| B3 | `rev * 1001` | a whole number above 1000 |
| B4 | `a / (b - b)` | division by zero |
| B5 | `a`, operands a and b | b is given and not used |
| B6 | `a + c`, operand a only | c is no operand |
| B7 | `a ** 2` | the power is not admitted |
| B8 | `abs(a)` | a call is not admitted |
| B9 | `a` with tier "owner" | the tier is none of verified, sourced, computed, judgement |
| B10 | `a + b`, a USD/shares, b USD | the units differ |
| B11 | an empty expression; one of 501 characters | empty or too long |

### C. Rules

- A result is tagged computed. Where any operand is of tier judgement,
  the result says it rests on a judgement and names those operands.
- A constant the expression needs that is a figure (a rate, a growth, a
  required return) is an operand stated with its origin, never a literal.
- The exact value is kept; only the said value is rounded (A7, A9).

