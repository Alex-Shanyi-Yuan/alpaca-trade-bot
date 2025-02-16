import os
import vectorbt as vbt
import datetime
import numpy as np
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Load API keys
load_dotenv()
API_KEY = os.getenv('ALPACA_KEY')
API_SECRET = os.getenv('ALPACA_SECRET')

# 1. Fetch data
data_client = StockHistoricalDataClient(API_KEY, API_SECRET)
bars = data_client.get_stock_bars(
    StockBarsRequest(
        symbol_or_symbols="SPY",
        timeframe=TimeFrame.Day,
        start=datetime.datetime(2020, 1, 1),
        end=datetime.datetime(2023, 1, 1)
    )
)
df = bars.df

# 2. Calculate indicators: 50-day and 200-day simple moving averages
df['sma_50'] = df['close'].rolling(50).mean()
df['sma_200'] = df['close'].rolling(200).mean()

# 3. Define improved strategy (Dual Moving Average Crossover)
# Entry when price crosses above the 50-day SMA and the 50-day SMA is above the 200-day SMA.
entries = (
    (df['close'] > df['sma_50']) & 
    (df['close'].shift(1) <= df['sma_50'].shift(1)) & 
    (df['sma_50'] > df['sma_200'])
)

# Exit when price crosses below the 50-day SMA or the trend reverses (50-day SMA falls below 200-day SMA).
exits = (
    ((df['close'] < df['sma_50']) & (df['close'].shift(1) >= df['sma_50'].shift(1))) | 
    (df['sma_50'] < df['sma_200'])
)

# 4. Run backtest
pf = vbt.Portfolio.from_signals(
    close=df['close'],
    entries=entries,
    exits=exits,
    sl_stop=0.02,  # 2% stop-loss
    tp_stop=0.04,  # 4% take-profit
    fees=0.001,
    freq='D'
)

# 5. Analyze results
print(pf.stats())
pf.plot().show()
