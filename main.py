from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    from datetime import datetime

    import pandas as pd

    from gui.chart_window.chart import DataChart
    from gui.chart_window.chart_window import ChartWindow
    from FMP.hourly_data import fmp_get_hourly_dataframe

    SYMBOL = "AAPL"
    START_DATE = datetime(2000, 1, 1)
    END_DATE = datetime.now()

    data = fmp_get_hourly_dataframe(SYMBOL, START_DATE, END_DATE)
    if data.empty:
        print(f"No hourly data returned for {SYMBOL}.")
    else:
        chart_data = data.copy()
        chart_data["date"] = pd.to_datetime(chart_data["date"], errors="coerce")
        chart_data["close"] = pd.to_numeric(chart_data["close"], errors="coerce")
        chart_data["volume"] = pd.to_numeric(chart_data["volume"], errors="coerce").fillna(
            0.0
        )
        chart_data = chart_data.loc[
            chart_data["date"].notna() & chart_data["close"].gt(0)
        ].copy()

        if chart_data.empty:
            print(f"No valid hourly rows remained for {SYMBOL}.")
            raise SystemExit(0)

        chart = DataChart(
            chart_data,
            title=f"{SYMBOL} Hourly Price and Script Features",
            y_label="Price",
        )
        window = ChartWindow(chart)
        window.show()
