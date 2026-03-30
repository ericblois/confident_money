# Condition Script Guide

## Quick Links
- [Script Basics](#script-basics)
- [Values and References](#values-and-references)
- [Operator Reference](#operator-reference)
- [Parameter Reference](#parameter-reference)
- [Core Functions](#core-functions)
- [Utility Functions](#utility-functions)
- [Trend Functions](#trend-functions)
- [Momentum Functions](#momentum-functions)
- [Relative Functions](#relative-functions)
- [Volatility Functions](#volatility-functions)
- [Volume Functions](#volume-functions)
- [Calendar Functions](#calendar-functions)
- [Candle Functions](#candle-functions)
- [Alias Functions](#alias-functions)
- [Rules and Gotchas](#rules-and-gotchas)

## Script Basics
Condition scripts are expressions evaluated against the chart's data over time. A buy or sell condition must finish as a boolean expression.

```txt
mv_avg(close, 20) > mv_avg(close, 50) and rsi() < 70
close crosses ema(close, 21)
vlt(20) < realized_vol(60) and volume > mv_avg(volume, 10)
```

- Bare identifiers like `close`, `volume`, or `my_custom_field` read named chart fields directly.
- Function calls can be nested inside other function calls.
- Numbers like `14` and `2.5`, booleans like `True` and `False`, and strings like `"2024-01-01"` are supported.
- Keyword arguments are not supported. Use positional arguments only.

## Values and References
- Any named chart field can be referenced directly by name.
- In this guide, a "field" means a named stream of values across chart timestamps, such as `close`, `high`, `volume`, or a custom imported field.
- `price` is special: if there is no `price` field, it falls back to `close`.
- `date` is treated as the main timestamp-friendly field name.
- A bare identifier such as `close` refers to the field itself, not a string literal.
- Parameters that accept `string` can also take a quoted field name such as `"close"`.
- Parameters named `source`, `left`, and `right` are numeric-only. Pass `close`, `ema(close, 20)`, or another numeric expression, not `"close"`.

## Operator Reference
### Arithmetic
| Operator | Meaning | Notes |
| --- | --- | --- |
| `+` | Addition | Numeric only |
| `-` | Subtraction | Numeric only |
| `*` | Multiplication | Numeric only |
| `/` | Division | Numeric only |
| `%` | Modulo | Numeric only |
| `**` | Exponentiation | Numeric only |
| Unary `+` | Positive value passthrough | Numeric only |
| Unary `-` | Negation | Numeric only |

### Comparison
| Operator | Meaning | Notes |
| --- | --- | --- |
| `==` | Equal to | Works on numbers, booleans, and strings |
| `!=` | Not equal to | Works on numbers, booleans, and strings |
| `>` | Greater than | Usually numeric |
| `>=` | Greater than or equal to | Usually numeric |
| `<` | Less than | Usually numeric |
| `<=` | Less than or equal to | Usually numeric |
| `crosses` | Crosses above | `left` must be above `right` now and at or below it on the previous bar/timestamp |

### Logical
| Operator | Meaning | Notes |
| --- | --- | --- |
| `not` | Boolean negation | Boolean only |
| `and` | Boolean AND | Evaluated timestamp by timestamp |
| `or` | Boolean OR | Evaluated timestamp by timestamp |

### Precedence
Operators are applied in this order, from highest to lowest:

1. Parentheses and function calls
2. `**`
3. Unary `+` and unary `-`
4. `*`, `/`, `%`
5. `+`, `-`
6. Comparisons: `==`, `!=`, `>`, `>=`, `<`, `<=`, `crosses`
7. `not`
8. `and`
9. `or`

### Chaining
- Standard comparison chaining is supported: `20 < rsi() < 80`.
- Chained comparisons behave like an `and`: `a < b < c` becomes `(a < b) and (b < c)`.
- `crosses` cannot be chained with other comparisons.

## Parameter Reference
Type labels below use script types:

- `number`: a numeric literal, bare field name, or numeric expression
- `string`: a string literal, usually used to name a field
- `boolean`: `True` or `False`

### Series and Column Parameters
| Parameter | Type | Meaning |
| --- | --- | --- |
| `benchmark` | `number or string` | Benchmark values or benchmark field |
| `benchmark_return` | `number or string` | Benchmark return values or field |
| `close` | `number or string` | Closing-price values or field |
| `col` | `number or string` | General input field/value stream used by many base functions |
| `high` | `number or string` | High-price values or field |
| `left` | `number` | Left-hand numeric expression, mainly for `distance()` |
| `low` | `number or string` | Low-price values or field |
| `open` | `number or string` | Opening-price values or field |
| `price` | `number or string` | Price values or field; often defaults to `close` |
| `reference` | `number or string` | Reference values/field for comparisons like `dist()` |
| `rel_return` | `number or string` | Relative return values or field |
| `return` | `number or string` | Return values or field |
| `right` | `number` | Right-hand numeric expression, mainly for `distance()` |
| `source` | `number` | Generic numeric input expression used by alias-style functions |
| `timestamp` | `number or string` | Timestamp/date values or field, usually defaulting to `date` |
| `volatility` | `number or string` | Volatility values or field |
| `volume` | `number or string` | Volume values or field |

### Window and Numeric Control Parameters
| Parameter | Type | Meaning |
| --- | --- | --- |
| `annualization_factor` | `number` | Optional annualization scale for volatility estimators |
| `ddof` | `number` | Degrees of freedom used by `z()` when computing rolling standard deviation |
| `fast_span` | `number` | Fast EMA span for MACD-style calculations |
| `min_periods` | `number` | Minimum valid timestamps/bars required inside a lookback window |
| `offset` | `number` | Non-negative backward shift used to reference earlier bars |
| `signal_min_periods` | `number` | Minimum valid timestamps used in the `stoch_d()` smoothing step |
| `signal_span` | `number` | Signal EMA span for MACD signal and histogram |
| `signal_window` | `number` | Signal smoothing window for `stoch_d()` |
| `slow_span` | `number` | Slow EMA span for MACD-style calculations |
| `span` | `number` | EMA span |
| `window` | `number` | Main lookback window |

### Boolean Flags
| Parameter | Type | Meaning |
| --- | --- | --- |
| `adjust` | `boolean` | Whether EMA-style calculations use adjusted weighting |
| `benchmark_is_return` | `boolean` | Whether `benchmark` already contains returns in `rel_ret()` |

## Core Functions
- `px()`, `px(price)`, `px(price, offset)`: Price values over time. Defaults to `close`; `offset` shifts backward by `offset` bars.
- `ret()`, `ret(col)`, `ret(col, window)`, `ret(col, window, offset)`: Simple return over `window`. Defaults to `close`, `window=1`, and `offset=0`.
- `log_ret(col, window)`, `log_ret(col, window, offset)`: Difference over `window` on the supplied values. This is most useful when the input is already log-transformed.
- `roll_hi()`, `roll_hi(col)`, `roll_hi(col, window)`, `roll_hi(col, window, min_periods)`, `roll_hi(col, window, min_periods, offset)`: Rolling maximum. Defaults to `col=high`, `window=20`, and `offset=0`; if omitted, `min_periods` behaves like `window`.
- `roll_lo()`, `roll_lo(col)`, `roll_lo(col, window)`, `roll_lo(col, window, min_periods)`, `roll_lo(col, window, min_periods, offset)`: Rolling minimum. Defaults to `col=low`, `window=20`, and `offset=0`; if omitted, `min_periods` behaves like `window`.
- `typ_px()`, `typ_px(high)`, `typ_px(high, low)`, `typ_px(high, low, close)`, `typ_px(high, low, close, offset)`: Typical price, or `(high + low + close) / 3`. Defaults to `high`, `low`, `close`, and `offset=0`.
- `med_px()`, `med_px(high)`, `med_px(high, low)`, `med_px(high, low, offset)`: Median price, or `(high + low) / 2`. Defaults to `high`, `low`, and `offset=0`.

## Utility Functions
- `abs(col)`: Absolute value of a numeric value stream.
- `log(col)`: Natural log of a value stream. Non-positive values become `NaN`.
- `dist(col, reference)`: Natural log distance, or `log(col / reference)`.
- `pct_rank(col, window)`, `pct_rank(col, window, min_periods)`: Rolling percentile rank of the current value inside the window, scaled to `0` through `100`.
- `z(col, window)`, `z(col, window, min_periods)`, `z(col, window, min_periods, ddof)`: Rolling z-score. `ddof` defaults to `0`.

## Trend Functions
- `ma(col, window)`, `ma(col, window, min_periods)`: Simple moving average. `min_periods` defaults to `1`.
- `ema(col, span)`, `ema(col, span, min_periods)`, `ema(col, span, min_periods, adjust)`: Exponential moving average. Defaults to `min_periods=1` and `adjust=False`.
- `trend_slp(col, window)`: Rolling linear-regression slope over `window`.
- `trend_r2(source, window)`: Rolling linear-regression R-squared over `window`.
- `brk_dist(col, window)`, `brk_dist(col, window, min_periods)`: Log distance from the prior rolling high. If omitted, `min_periods` behaves like `window`.
- `rng_pos(col, window)`, `rng_pos(col, window, min_periods)`: Current value's normalized position inside the prior rolling range, usually between `0` and `1`.
- `adx(window)`, `adx(window, high)`, `adx(window, high, low)`, `adx(window, high, low, close)`, `adx(window, high, low, close, min_periods)`: Average Directional Index. Defaults to `high`, `low`, and `close`; if omitted, `min_periods` behaves like `window`.

## Momentum Functions
- `macd()`, `macd(col)`, `macd(col, fast_span)`, `macd(col, fast_span, slow_span)`, `macd(col, fast_span, slow_span, min_periods)`: MACD line, or fast EMA minus slow EMA. Defaults to `col=close`, `fast_span=12`, `slow_span=26`, `min_periods=1`; `fast_span` must be smaller than `slow_span`.
- `macd_sig()`, `macd_sig(col)`, `macd_sig(col, fast_span)`, `macd_sig(col, fast_span, slow_span)`, `macd_sig(col, fast_span, slow_span, signal_span)`, `macd_sig(col, fast_span, slow_span, signal_span, min_periods)`: MACD signal line. Defaults mirror `macd()`, with `signal_span=9`.
- `macd_hist()`, `macd_hist(col)`, `macd_hist(col, fast_span)`, `macd_hist(col, fast_span, slow_span)`, `macd_hist(col, fast_span, slow_span, signal_span)`, `macd_hist(col, fast_span, slow_span, signal_span, min_periods)`: MACD histogram, or MACD line minus signal line.
- `mom(return, volatility)`: Momentum, calculated as return divided by volatility.
- `roc()`, `roc(col)`, `roc(col, window)`: Percentage rate of change. Defaults to `col=close` and `window=10`.
- `rsi()`, `rsi(col)`, `rsi(col, window)`, `rsi(col, window, min_periods)`: Relative Strength Index, usually in the `0` to `100` range. Defaults to `col=close` and `window=14`; if omitted, `min_periods` behaves like `window`.
- `stoch_k()`, `stoch_k(window)`, `stoch_k(window, high)`, `stoch_k(window, high, low)`, `stoch_k(window, high, low, close)`, `stoch_k(window, high, low, close, min_periods)`: Stochastic `%K`, usually in the `0` to `100` range. Defaults to `window=14`, `high`, `low`, and `close`.
- `stoch_d()`, `stoch_d(window)`, `stoch_d(window, signal_window)`, `stoch_d(window, signal_window, high)`, `stoch_d(window, signal_window, high, low)`, `stoch_d(window, signal_window, high, low, close)`, `stoch_d(window, signal_window, high, low, close, min_periods)`, `stoch_d(window, signal_window, high, low, close, min_periods, signal_min_periods)`: Smoothed stochastic `%D`. Defaults to `window=14`, `signal_window=3`, `signal_min_periods=1`, and the standard `high`, `low`, and `close` fields.
- `will_r()`, `will_r(window)`, `will_r(window, high)`, `will_r(window, high, low)`, `will_r(window, high, low, close)`, `will_r(window, high, low, close, min_periods)`: Williams `%R`, usually in the `-100` to `0` range. Defaults to `window=14` and the standard `high`, `low`, and `close` fields.

## Relative Functions
- `rel_ret(return, benchmark, window)`, `rel_ret(return, benchmark, window, benchmark_is_return)`: Relative return versus a benchmark. If `benchmark_is_return=False`, the benchmark is first converted to a `window` return; if `True`, it is used directly.
- `rel_mom(rel_return, return, benchmark_return, window)`, `rel_mom(rel_return, return, benchmark_return, window, min_periods)`: Relative momentum, or relative return divided by tracking volatility.
- `rel_trend_slp(col, benchmark, window)`: Trend slope of `col - benchmark`.
- `rel_trend_r2(source, benchmark, window)`: Trend R-squared of `source - benchmark`.

## Volatility Functions
- `tr()`, `tr(high)`, `tr(high, low)`, `tr(high, low, close)`: True range. Defaults to standard `high`, `low`, and `close`.
- `atr(window)`, `atr(window, high)`, `atr(window, high, low)`, `atr(window, high, low, close)`, `atr(window, high, low, close, min_periods)`: Average True Range using Wilder smoothing. Defaults to the standard `high`, `low`, and `close` fields; if omitted, `min_periods` behaves like `window`.
- `vlt(window)`, `vlt(source, window)`, `vlt(source, window, min_periods)`: Realized volatility. With one argument it uses log returns of `close`; with `source` it uses the supplied numeric value stream directly. If omitted, `min_periods` behaves like `window`.
- `pk_vlt(window)`, `pk_vlt(window, high)`, `pk_vlt(window, high, low)`, `pk_vlt(window, high, low, min_periods)`, `pk_vlt(window, high, low, min_periods, annualization_factor)`: Parkinson volatility estimator. Defaults to `high`, `low`, and window-based `min_periods`.
- `gk_vlt(window)`, `gk_vlt(window, open)`, `gk_vlt(window, open, high)`, `gk_vlt(window, open, high, low)`, `gk_vlt(window, open, high, low, close)`, `gk_vlt(window, open, high, low, close, min_periods)`, `gk_vlt(window, open, high, low, close, min_periods, annualization_factor)`: Garman-Klass volatility estimator using OHLC data.
- `rs_vlt(window)`, `rs_vlt(window, open)`, `rs_vlt(window, open, high)`, `rs_vlt(window, open, high, low)`, `rs_vlt(window, open, high, low, close)`, `rs_vlt(window, open, high, low, close, min_periods)`, `rs_vlt(window, open, high, low, close, min_periods, annualization_factor)`: Rogers-Satchell volatility estimator using OHLC data.

## Volume Functions
- `vol()`, `vol(col)`, `vol(col, offset)`: Volume values over time. Defaults to `col=volume` and `offset=0`.
- `vwap(window)`, `vwap(window, price)`, `vwap(window, price, volume)`, `vwap(window, price, volume, min_periods)`: Rolling volume-weighted average price. Defaults to `price=close`, `volume=volume`, and window-based `min_periods`.
- `obv()`, `obv(close)`, `obv(close, volume)`: On-Balance Volume. Defaults to standard `close` and `volume`.
- `adl()`, `adl(high)`, `adl(high, low)`, `adl(high, low, close)`, `adl(high, low, close, volume)`: Accumulation/Distribution Line. Defaults to the standard `high`, `low`, `close`, and `volume` fields.
- `cmf(window)`, `cmf(window, high)`, `cmf(window, high, low)`, `cmf(window, high, low, close)`, `cmf(window, high, low, close, volume)`, `cmf(window, high, low, close, volume, min_periods)`: Chaikin Money Flow over a rolling window.
- `mfi()`, `mfi(window)`, `mfi(window, high)`, `mfi(window, high, low)`, `mfi(window, high, low, close)`, `mfi(window, high, low, close, volume)`, `mfi(window, high, low, close, volume, min_periods)`: Money Flow Index, usually in the `0` to `100` range. Defaults to `window=14` and the standard `high`, `low`, `close`, and `volume` fields.
- `rvol_pct(window)`, `rvol_pct(window, volume)`, `rvol_pct(window, volume, min_periods)`: Rolling percentile rank of volume, scaled to `0` through `100`.

## Calendar Functions
These functions return numeric calendar features, not booleans. The default timestamp field is `date`.

- `dow()`, `dow(timestamp)`: Day of week, where Monday is `0`.
- `dom()`, `dom(timestamp)`: Day of month.
- `doy()`, `doy(timestamp)`: Day of year.
- `woy()`, `woy(timestamp)`: ISO week of year.
- `moy()`, `moy(timestamp)`: Month of year.
- `qtr()`, `qtr(timestamp)`: Quarter number.
- `hour()`, `hour(timestamp)`: Hour of day.
- `is_ms()`, `is_ms(timestamp)`: Month-start flag returned as `0` or `1`.
- `is_me()`, `is_me(timestamp)`: Month-end flag returned as `0` or `1`.
- `is_hol_adj()`, `is_hol_adj(timestamp)`: US federal-holiday adjacency flag returned as `0` or `1`.

## Candle Functions
- `body_pct()`, `body_pct(open)`, `body_pct(open, close)`: Candle body percent, or `(close - open) / open`.
- `clv()`, `clv(high)`, `clv(high, low)`, `clv(high, low, close)`: Close location value inside the candle range.
- `up_wick()`, `up_wick(open)`, `up_wick(open, high)`, `up_wick(open, high, low)`, `up_wick(open, high, low, close)`: Upper wick size as a fraction of total candle range.
- `low_wick()`, `low_wick(open)`, `low_wick(open, high)`, `low_wick(open, high, low)`, `low_wick(open, high, low, close)`: Lower wick size as a fraction of total candle range.

## Alias Functions
These are alternate script terms that map to the same underlying calculations.

- `mv_avg(source, window)`, `mv_avg(source, window, min_periods)`: Alias of `ma`. `min_periods` defaults to `1`.
- `moving_avg(source, window)`, `moving_avg(source, window, min_periods)`: Alias of `ma`. `min_periods` defaults to `1`.
- `distance(left, right)`: Alias of `dist`, but takes generic numeric expressions instead of field-name-style inputs.
- `log_return(window)`, `log_return(source, window)`: Log return helper. The one-argument form uses `log(close)` automatically; the two-argument form uses the supplied `source`.
- `breakout_distance(source, window)`, `breakout_distance(source, window, min_periods)`: Alias of `brk_dist`.
- `range_position(source, window)`, `range_position(source, window, min_periods)`: Alias of `rng_pos`.
- `momentum(return, volatility)`: Alias of `mom`.
- `trend_slope(source, window)`: Alias of `trend_slp`.
- `rel_return(return, benchmark, window)`: Alias of `rel_ret(return, benchmark, window, False)`.
- `rel_momentum(rel_return, return, benchmark, window)`, `rel_momentum(rel_return, return, benchmark, window, min_periods)`: Alias of `rel_mom`.
- `rel_trend_slope(source, benchmark, window)`: Alias of `rel_trend_slp`.
- `realized_vol(window)`, `realized_vol(source, window)`, `realized_vol(source, window, min_periods)`: Alias of `vlt`.

## Rules and Gotchas
- Final buy/sell conditions must evaluate to a boolean expression.
- Function arguments are positional only. `ema(col=close, span=20)` is not valid.
- `crosses` means "crosses above", not "crosses in either direction".
- `crosses` does not support chaining, so `a crosses b < c` is invalid.
- Arithmetic operators require numeric expressions.
- `not`, `and`, and `or` require boolean expressions.
- Most rolling parameters such as `window`, `span`, `fast_span`, `slow_span`, and `min_periods` must be positive integers.
- `offset` must be a non-negative integer.
- `macd()` requires `fast_span < slow_span`.
- `log_ret(col, window)` and `log_return(...)` are not the same convenience level:
  - `log_ret(col, window)` takes differences on the values you pass in.
  - `log_return(window)` first takes `log(close)` for you, then computes the difference.
- `vlt(window)` and `realized_vol(window)` also have a convenience form:
  - One argument means "compute log returns of `close`, then realized volatility over `window`".
  - Passing `source` means "use this value stream directly".
- A quoted field name like `"close"` only works for parameters that accept `string`.
- For alias-style `source` parameters, use `close`, `price`, `ema(close, 20)`, or another numeric expression instead of `"close"`.
