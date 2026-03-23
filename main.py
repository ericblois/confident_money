from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    from datetime import datetime

    from chart import DataChart
    from FMP.hourly_data import fmp_get_hourly_dataframe

    symbol = "SPY"
    start_date = datetime(2000, 1, 1)
    end_date = datetime.now()

    data = fmp_get_hourly_dataframe(symbol, start_date, end_date)
    if data.empty:
        print(f"No hourly data returned for {symbol}.")
    else:
        chart = DataChart(data, title=f"{symbol} Hourly Close")
        chart.add_close_line()
        chart.show()
