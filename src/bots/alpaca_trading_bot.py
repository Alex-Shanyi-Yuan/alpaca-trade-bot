import time
import logging
import datetime

from alpaca.trading.client import TradingClient # allows making request
from alpaca.trading.requests import MarketOrderRequest # by stock on market price
from alpaca.trading.enums import (
    OrderSide, # buy or sell type
    TimeInForce, # order valid time frame type
    AssetClass, # get asset type
)
from alpaca.data.timeframe import TimeFrame # import TimeFrame
from alpaca.data.historical import StockHistoricalDataClient # get historical data
from alpaca.data.requests import StockLatestQuoteRequest # stock current information
from alpaca.data.requests import StockBarsRequest # stock bar information
from alpaca.data.requests import StockQuotesRequest # get more info then just the latests

# configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlpacaTradingBot:
    def __init__(self, key, secret, base_url=None): # base_url not needed yet
        self.trading_client = TradingClient(key, secret, paper=True)
        self.data_client = StockHistoricalDataClient(key, secret)
        self.symbol = 'TSLA' # doing tesla stock
        self.equity = None # not need yet
        self.max_orders = 3 # max number of posiiton allowed
        self.quantity = 2 # number of shares to trade
        self.stop_loss_pct = 0.01 # iniitilize to be 1%
        self.take_profit_pct = 0.02 # initialize to be 2%
        self.can_trade = True
        self.position_count = 0
        self.last_trade_time = None
        self.current_candle_end = None
        self.candle_interval = 15  # minutes

    def get_latest_price(self):
        """Get latest price"""
        try:
            request_param = StockLatestQuoteRequest(symbol_or_symbols=[self.symbol])
            latest_quote = self.data_client.get_stock_latest_quote(request_param)
            return latest_quote[self.symbol]
        except Exception as e:
            logger.error(f"Error getting price: {e}")
            return None
    
    def get_historical_high_low(self):
        """Get previous candle's high/low"""
        try:
            request = StockBarsRequest(
                symbol=self.symbol,
                timeframe=TimeFrame.Minute,
                start=datetime.datetime.now() - datetime.timedelta(minutes=10),
                limit=2
            )
            bars = self.data_client.get_stock_bars(request)
            return bars[-2].high, bars[-2].low if len(bars) >= 2 else None, None
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return None, None

    def check_positions(self):
        """count open positions for current symbol"""
        try:
            positions = self.trading_client.get_all_positions()
            return len([p for p in positions if p.symbol == self.symbol])
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return 0
    
    def place_bracket_order(self, side):
        """Place order with stop loss and take profit"""
        try:
            # get latest prices
            price = self.get_latest_price()
            # skip when error occured
            if price is None:
                return False
            # calculation stop loss and take profit prices
            current_price = price.bid_price
            stop_loss_price = current_price * (1-self.stop_loss_pct) if side==OrderSide.BUY else current_price * (1+self.stop_loss_pct)
            take_profit_price = current_price * (1+self.take_profit_pct) if side==OrderSide.BUY else current_price * (1-self.take_profit_pct)
            # construct order request
            order_params = MarketOrderRequest(
                symbol=self.symbol,
                qty=self.quantity,
                side=side,
                time_in_force=TimeInForce.DAY,
                order_class="bracket",
                stop_loss={"stop_price": round(stop_loss_price, 2)},
                take_profit={"limit_price": round(take_profit_price, 2)}
            )
            # make order
            order = self.trading_client.submit_order(order_params)
            self.last_trade_time = datetime.datetime.now(datetime.timezone.utc)
            self.can_trade = False
            logger.info(f"Trade executed at {self.last_trade_time}")
            return True
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return False
        
    def _update_candle_time(self, current_time):
        """Calculate next candel end time (e.g., 15-minutes aligned)"""
        minute = current_time.minute
        remainder = minute % self.candle_interval
        next_candle = current_time + datetime.timedelta(minutes=self.candle_interval - remainder)
        
        self.current_candle_end = next_candle.replace(second=0, microsecond=0)

    def _should_reset_trading_flag(self, current_time):
        """Check both cooldown and candle conditions"""
        # 1. Cooldown check (minimum 5 minutes between trades)
        if self.last_trade_time:
            cooldown_elapsed = (current_time - self.last_trade_time).total_seconds() >= 300  # 5 minutes
        else:
            cooldown_elapsed = True

        # 2. New candle check (15-minute intervals)
        if not self.current_candle_end:
            self._update_candle_time(current_time)
            return False

        new_candle_started = current_time >= self.current_candle_end
        if new_candle_started:
            self._update_candle_time(current_time)

        return cooldown_elapsed and new_candle_started

    def trade_logic(self):
        prev_high, prev_low = self.get_historical_high_low()
        latest_quote = self.get_latest_price()
        if not prev_high or not prev_low or not latest_quote:
            return

        current_price = latest_quote.bid_price
        self.position_count = self.check_positions()

        if self.position_count < self.max_orders and self.can_trade: # stock trend goes up
            if current_price > prev_high * 1.001:  # Breakout with 0.1% buffer
                self.place_bracket_order(OrderSide.BUY) # stock trend goes down
            elif current_price < prev_low * 0.999:  # Breakdown with 0.1% buffer
                self.place_bracket_order(OrderSide.SELL)

    def run(self):
        """Main execution loop"""
        logger.info("Start trading bot...")
        try:
            while True:
                if not self.is_market_open():
                    logger.info("Market closed, waiting till it open")
                    time.sleep(60)
                    continue

                # reset can_trade only if:
                # 1. cooldown period has passed
                # 2. new candle has started
                now = datetime.datetime.now(datetime.timezone.utc)
                if self._should_reset_trading_flag(now):
                    self.can_trade = True
                    logger.info("enable can trade flag")

                self.trade_logic()
                time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Stoping bot...")
            self.close_all_position_and_order()

    def close_all_position_and_order(self):
        """Closes all the position for symbol"""
        try:
            self.trading_client.close_all_positions(cancel_orders=True)
            logger.info("Closed all positions and orders")
        except Exception as e:
            logger.error(f"Error closing positison!!!! {e}")
    
    def is_market_open(self):
        """Check if market is open currently"""
        clock = self.trading_client.get_clock()
        return clock.is_open
