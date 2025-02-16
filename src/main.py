import os
from dotenv import load_dotenv
from bots.alpaca_trading_bot import AlpacaTradingBot

load_dotenv()

API_KEY = os.getenv('ALPACA_KEY')
API_SECRET = os.getenv('ALPACA_SECRET')

if __name__ == "__main__":
    bot = AlpacaTradingBot(API_KEY, API_SECRET)
    bot.run()
