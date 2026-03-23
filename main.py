from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    from FMP.hourly_data import fmp_get_hourly_dataframe
    from datetime import datetime

    symbol = "SPY"
    start_date = datetime(2000, 1, 1)
    end_date = datetime.now()

    data = fmp_get_hourly_dataframe(symbol, start_date, end_date)
    print(data)