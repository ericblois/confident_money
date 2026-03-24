from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    from datetime import datetime

    from analysis.momentum import add_hourly_momentum_columns
    from chart import DataChart
    from FMP.hourly_data import fmp_get_hourly_dataframe

    symbol = "AAPL"
    start_date = datetime(2000, 1, 1)
    end_date = datetime.now()

    data = fmp_get_hourly_dataframe(symbol, start_date, end_date)
    momentum_data = add_hourly_momentum_columns(data, market_dataframe=data)
    if momentum_data.empty:
        print(f"No hourly data returned for {symbol}.")
    else:
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
        chart.show()
