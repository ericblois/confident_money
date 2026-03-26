from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    from datetime import datetime

    import pandas as pd

    from features import (
        add_log_return,
        add_momentum,
        add_realized_vol,
        add_vwap,
        calc_log_value,
    )
    from gui.chart_window.chart import DataChart
    from gui.chart_window.chart_window import ChartWindow
    from FMP.hourly_data import fmp_get_hourly_dataframe

    symbol = "AAPL"
    start_date = datetime(2000, 1, 1)
    end_date = datetime.now()

    data = fmp_get_hourly_dataframe(symbol, start_date, end_date)
    if data.empty:
        print(f"No hourly data returned for {symbol}.")
    else:
        momentum_data = data.copy()
        momentum_data["timestamp"] = pd.to_datetime(momentum_data["date"], errors="coerce")
        momentum_data["close"] = pd.to_numeric(momentum_data["close"], errors="coerce")
        momentum_data["volume"] = pd.to_numeric(
            momentum_data["volume"],
            errors="coerce",
        ).fillna(0.0)
        momentum_data = momentum_data.loc[
            momentum_data["timestamp"].notna() & momentum_data["close"].gt(0)
        ].copy()

        if momentum_data.empty:
            print(f"No valid hourly rows remained for {symbol}.")
            raise SystemExit(0)

        momentum_data["trading_day"] = momentum_data["timestamp"].dt.normalize()
        daily_counts = momentum_data.groupby("trading_day")["timestamp"].size()
        bars_per_day = max(1, int(round(float(daily_counts.median()))))

        momentum_data["log_close"] = calc_log_value(momentum_data, "close")
        add_log_return(
            momentum_data,
            "log_close",
            1,
            output_col="log_return_1h",
        )
        for label, trading_days in {"1d": 1, "1w": 5, "1m": 21}.items():
            window = trading_days * bars_per_day
            log_return_col = f"log_return_{label}"
            realized_vol_col = f"realized_vol_{label}"
            add_log_return(
                momentum_data,
                "log_close",
                window,
                output_col=log_return_col,
            )
            add_realized_vol(
                momentum_data,
                "log_return_1h",
                window,
                output_col=realized_vol_col,
                min_periods=window,
            )
            add_momentum(
                momentum_data,
                log_return_col,
                realized_vol_col,
                output_col=f"momentum_{label}",
            )

        for trading_days in (20, 60):
            window = trading_days * bars_per_day
            add_vwap(
                momentum_data,
                window,
                output_col=f"vwap_{trading_days}d",
                min_periods=window,
            )

        chart = DataChart(
            momentum_data,
            title=f"{symbol} Hourly Price and Momentum",
            y_label="Price",
        )
        chart.add_close_line()
        chart.add_line(
            name="VWAP 20D",
            y="vwap_20d",
            color="#ef4444",
            width=1.5,
        )
        chart.add_line(
            name="VWAP 60D",
            y="vwap_60d",
            color="#f59e0b",
            width=1.5,
        )
        chart.add_pane("momentum", y_label="Momentum", height_ratio=1)
        chart.add_horizontal_line(
            name="Zero",
            y=0.0,
            pane="momentum",
            color="#94a3b8",
            width=1.25,
            dash="dash",
        )
        chart.add_line(
            name="Momentum 1D",
            y="momentum_1d",
            pane="momentum",
            color="#2563eb",
        )
        chart.add_line(
            name="Momentum 1W",
            y="momentum_1w",
            pane="momentum",
            color="#16a34a",
        )
        chart.add_line(
            name="Momentum 1M",
            y="momentum_1m",
            pane="momentum",
            color="#7c3aed",
        )
        window = ChartWindow(chart)
        window.show()
