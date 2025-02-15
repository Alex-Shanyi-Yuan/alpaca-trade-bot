# load env var
import os
from dotenv import load_dotenv

from datetime import datetime # handle datetime

from alpaca.trading.client import TradingClient # allow connect to account
from alpaca.data import StockHistoricalDataClient, StockTradesRequest # get historical data and trade request object
from alpaca.trading.requests import MarketOrderRequest # make trade request at current price of stock
from alpaca.trading.requests import LimitOrderRequest # make trade request at specified price of stock
from alpaca.trading.enums import OrderSide # OrderSide (buy or short) 
from alpaca.trading.enums import TimeInForce # TimeInForce (a day, immediently etc.)
from alpaca.trading.requests import GetOrdersRequest # reuqest to get current opened order
from alpaca.trading.enums import QueryOrderStatus # get order status types
from alpaca.data.live import StockDataStream # get trade info live

# account setup
load_dotenv()
ALPACA_KEY = os.getenv('ALPACA_KEY')
ALPACA_SECRET = os.getenv('ALPACA_SECRET')

# account access client
tradeing_client = TradingClient(ALPACA_KEY, ALPACA_SECRET)

# data getting client
data_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

# trade stream
# stream = StockDataStream(ALPACA_KEY, ALPACA_SECRET)
# async def handle_trade(data):
#     print(data)
# stream.subscribe_trades(handle_trade, 'AAPL')
# stream.run()

# print general account information
print(tradeing_client.get_account().account_number)
print(tradeing_client.get_account().buying_power)

# get current holdings:
positions = tradeing_client.get_all_positions()
for position in positions:
    print(position.symbol, position.current_price)

# liquidify all holdings:
# tradeing_client.close_all_positions(True)

# print trading informaiton
# request_param = StockTradesRequest(
#     symbol_or_symbols='AAPL', # apple stock
#     start=datetime(2025,2,14,14,30),
#     end=datetime(2025,2,14,14,45),
# ) # trade information within first 15 minutes of market open in utc time
# trades = data_client.get_stock_trades(request_param)
# print(trades.data['AAPL'][0])

# make a trade for the market price of apple
# market_order_param = MarketOrderRequest(
#     symbol='AAPL',
#     qty=1,
#     side=OrderSide.BUY,
#     time_in_force=TimeInForce.DAY
# )
# market_order = tradeing_client.submit_order(market_order_param)
# print(market_order)

# make limit buy at specified price
# limit_order_param = LimitOrderRequest(
#     symbol='AAPL',
#     qty=1,
#     side=OrderSide.BUY,
#     time_in_force=TimeInForce.DAY,
#     limit_price=240.84
# )
# limit_order = tradeing_client.submit_order(limit_order_param)
# print(limit_order)

# get current trade orders in the account
# request_params = GetOrdersRequest(
#     status=QueryOrderStatus.OPEN,
#     side=OrderSide.BUY,
# )
# orders = tradeing_client.get_orders(request_params)
# # cancel the order
# for order in orders:
#     tradeing_client.cancel_order_by_id(order.id)
#     print(f'canceled order number: {order.id}')