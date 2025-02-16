import time
import logging
import datetime
import os
import numpy as np
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/alex-shanyi-yuan/alpaca-trade-bot/day_trading.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load API keys
load_dotenv()
API_KEY = os.getenv('ALPACA_KEY')
API_SECRET = os.getenv('ALPACA_SECRET')

class AlpacaTradingBot:
    def __init__(self, symbol='SPY'):
        self.trading_client = TradingClient(API_KEY, API_SECRET, paper=True)
        self.data_client = StockHistoricalDataClient(API_KEY, API_SECRET)
        self.symbol = symbol
        self.quantity = 10  # Number of shares to trade
        self.stop_loss_pct = 0.02  # 2% stop-loss
        self.take_profit_pct = 0.04  # 4% take-profit

    def fetch_data(self):
        """Fetch latest historical data"""
        try:
            bars = self.data_client.get_stock_bars(
                StockBarsRequest(
                    symbol_or_symbols=self.symbol,
                    timeframe=TimeFrame.Day,
                    start=datetime.datetime.now() - datetime.timedelta(days=365),
                    limit=200  # Ensure enough data for SMA calculation
                )
            )
            return bars.df
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None

    def calculate_signals(self, df):
        """Calculate SMA crossover signals"""
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()
        
        df['buy_signal'] = (
            (df['close'] > df['sma_50']) &
            (df['close'].shift(1) <= df['sma_50'].shift(1)) &
            (df['sma_50'] > df['sma_200'])
        )
        
        df['sell_signal'] = (
            ((df['close'] < df['sma_50']) & (df['close'].shift(1) >= df['sma_50'].shift(1))) | 
            (df['sma_50'] < df['sma_200'])
        )
        
        return df

    def get_latest_price(self):
        """Get latest price"""
        try:
            request_param = StockLatestQuoteRequest(symbol_or_symbols=[self.symbol])
            latest_quote = self.data_client.get_stock_latest_quote(request_param)
            return latest_quote[self.symbol]
        except Exception as e:
            logger.error(f"Error getting price: {e}")
            return None

    def place_bracket_order(self, side):
        """Place an order with stop loss and take profit"""
        try:
            latest_quote = self.get_latest_price()
            if latest_quote is None:
                return False
            
            current_price = latest_quote.bid_price
            stop_loss_price = current_price * (1 - self.stop_loss_pct) if side == OrderSide.BUY else current_price * (1 + self.stop_loss_pct)
            take_profit_price = current_price * (1 + self.take_profit_pct) if side == OrderSide.BUY else current_price * (1 - self.take_profit_pct)

            order_params = MarketOrderRequest(
                symbol=self.symbol,
                qty=self.quantity,
                side=side,
                time_in_force=TimeInForce.DAY,
                order_class="bracket",
                stop_loss={"stop_price": round(stop_loss_price, 2)},
                take_profit={"limit_price": round(take_profit_price, 2)}
            )
            self.trading_client.submit_order(order_params)
            logger.info(f"Placed {side.name} order for {self.symbol} at {current_price}")
            return True
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return False

    def execute_trades(self):
        """Execute buy/sell trades based on strategy"""
        df = self.fetch_data()
        if df is None or len(df) < 200:
            logger.error("Not enough data to calculate indicators.")
            return

        df = self.calculate_signals(df)
        latest_signal = df.iloc[-1]
        if latest_signal['buy_signal']:
            self.place_bracket_order(OrderSide.BUY)
        elif latest_signal['sell_signal']:
            self.place_bracket_order(OrderSide.SELL)

    def run(self):
        """Run bot once per day in the last hour before market close"""
        logger.info("Running daily trade execution...")
        self.execute_trades()
        logger.info("Execution completed.")

if __name__ == "__main__":
    bot = AlpacaTradingBot()
    bot.run()

    logger.info("")

