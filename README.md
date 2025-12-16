Simplified Binance Trading Bot
A production-ready Python trading bot for Binance Futures Testnet with support for multiple advanced order types, comprehensive logging, and an intuitive CLI interface.

┌─────────────────────────────────────────────────────────────┐
│                    User Interface (CLI)                      │
│                   TradingBotCLI Class                        │
│         - display_menu()                                     │
│         - handle_* methods                                   │
│         - input validation                                   │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│              Trading Bot Core Logic                          │
│            BinanceTradingBot Class                           │
│         - place_market_order()                               │
│         - place_limit_order()                                │
│         - place_stop_limit_order()                           │
│         - place_oco_order()                                  │
│         - place_grid_order()                                 │
│         - place_twap_order()                                 │
│         - order management methods                           │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│              Binance API Integration                         │
│            Python-Binance Client                            │
│         - futures_account()                                  │
│         - futures_create_order()                             │
│         - futures_cancel_order()                             │
│         - futures_get_open_orders()                          │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│          Binance Futures Testnet REST API                    │
│      https://testnet.binancefuture.com/fapi                  │
└───────



✨ Features
Core Order Types
Market Orders - Execute immediately at current market price

Limit Orders - Execute at specified price or better

Stop-Limit Orders - Trigger stop price, then limit order

One-Cancels-Other (OCO) - Profit-taking + Stop-loss pair

Grid Trading - Distribute orders across multiple price levels

TWAP (Time-Weighted Average Price) - Slice orders over time

Additional Features
✅ Full Binance Futures Testnet support (risk-free testing)

✅ Comprehensive logging (file + console)

✅ Account balance and position tracking

✅ Open order management

✅ Order history tracking

✅ User-friendly CLI interface

✅ Error handling and validation

✅ Real-time order status monitoring

📋 Requirements
System Requirements
Python 3.8+

pip package manager

Internet connection

Binance Testnet account

Python Dependencies
text
python-binance>=1.0.17
requests>=2.28.0
colorama>=0.4.6
tabulate>=0.9.0
🚀 Installation
1. Clone or Download
bash
git clone <repository-url>
cd trading-bot
2. Install Dependencies
bash
pip install -r requirements.txt
Or install manually:

bash
pip install python-binance requests colorama tabulate
3. Set Up Binance Testnet Account
Visit: https://testnet.binancefuture.com

Sign up or login with existing Binance account

Navigate to Account → API Management

Create new API key with Futures permissions

Copy your API key and API secret (keep them secure!)

4. Run the Bot
bash
python trading_bot.py
📖 Usage Guide
Starting the Bot
bash
python trading_bot.py
When prompted:

Enter your Binance Testnet API Key

Enter your Binance Testnet API Secret

Main Menu Options
1. Account & Balance
1.1 Check Account Balance

View total wallet balance

Available and used margin

Margin level

1.2 Check Open Orders

View all open orders

Filter by symbol (optional)

2. Place Orders
2.1 Market Order
Fastest execution at current market price

Best for: Immediate execution

text
Symbol: BTCUSDT
Side: BUY
Quantity: 0.01
2.2 Limit Order
Execute at specific price or better

Best for: Price control

text
Symbol: ETHUSDT
Side: SELL
Quantity: 1.0
Price: 2500
2.3 Stop-Limit Order
Trigger at stop price, execute at limit price

Best for: Risk management, exit strategies

text
Symbol: BNBUSDT
Side: SELL
Quantity: 10
Stop Price: 500
Limit Price: 495
2.4 OCO Order
Combines limit order (profit-taking) + stop order (stop-loss)

Best for: Automated profit/loss management

text
Symbol: ADAUSDT
Side: BUY
Quantity: 100
Limit Price: 1.2 (profit target)
Stop Price: 0.8 (stop loss)
2.5 Grid Orders
Distribute orders across multiple price levels

Best for: Ranging markets, dollar-cost averaging

text
Symbol: DOGEUSDT
Side: BUY
Total Quantity: 1000
Base Price: 0.25
Grid Levels: 5 (creates 5 orders)
Grid Percentage: 2.0 (2% spacing between levels)
2.6 TWAP Orders
Execute total quantity as slices over time

Best for: Large orders, minimizing market impact

text
Symbol: LTCUSDT
Side: BUY
Total Quantity: 10
Number of Slices: 5 (executes 2 LTC per slice)
Interval: 60 (seconds between slices)
3. Manage Orders
3.1 Get Order Status

Check if order is open, filled, or rejected

View execution details

3.2 Cancel Order

Cancel open orders

Confirmation required for safety

4. View History
4.1 Display Order History

All orders placed in this session

Includes order types and timestamps

5. Exit
Gracefully shut down the bot

📝 Example Workflows
Workflow 1: Simple Buy and Sell
text
1. Place market buy order
2. Wait for confirmation
3. Place limit sell order at target price
4. Monitor from "Check Open Orders"
5. Order executes when price reaches target
Workflow 2: Risk-Managed Entry
text
1. Place OCO order (entry + take-profit + stop-loss)
2. Bot automatically manages exits
3. One of the two exit orders will execute
Workflow 3: Dollar-Cost Averaging
text
1. Use Grid orders to buy at multiple levels
2. Automatically distributes capital across prices
3. Reduces average entry price
Workflow 4: Large Order Execution
text
1. Use TWAP orders for discretion
2. Slices order over time to minimize slippage
3. Bot handles timing automatically
🔒 Security Best Practices
API Key Security

Use Testnet API keys for learning

Never commit API keys to version control

Use environment variables in production

Limit API key permissions

Order Safety

Start with small quantities

Test thoroughly on testnet

Use stop-loss orders

Monitor positions regularly

Account Security

Enable 2FA on Binance account

Use IP whitelisting for API keys

Monitor account activity

📊 Logging
Logs are saved to trading_bot.log with the following information:

All API requests and responses

Order placement and cancellation

Error conditions and exceptions

Balance updates

Timestamps for all actions

View logs:

bash
tail -f trading_bot.log
🐛 Troubleshooting
Issue: "Invalid API Key"
✅ Check API key is from Binance Testnet, not Mainnet

✅ Verify no extra spaces in key/secret

✅ Ensure API key has Futures permissions

Issue: "Insufficient Balance"
✅ Check account balance first (option 1.1)

✅ Testnet provides initial balance - might need to reset

✅ Verify order quantity

Issue: "Order Rejected"
✅ Check minimum notional value (~10 USDT)

✅ Verify symbol exists

✅ Check price is within acceptable range

✅ Review logs for specific error

Issue: "Connection Timeout"
✅ Check internet connection

✅ Verify Binance Testnet is online

✅ Try again after a few seconds

✅ Check firewall settings

📚 Code Structure
text
trading_bot.py
├── Configuration
│   ├── Environment (TESTNET/MAINNET)
│   ├── OrderType (MARKET, LIMIT, etc.)
│   └── OrderSide (BUY/SELL)
├── Logging Setup
│   └── setup_logging() - File + Console logging
├── Core Classes
│   ├── OrderConfig - Order data structure
│   ├── BinanceTradingBot - Main bot logic
│   └── TradingBotCLI - User interface
└── Main Entry Point
    └── main() - Initialization and startup
🔄 API Methods
Account Methods
python
bot.get_account_balance()          # Get balance info
bot.validate_symbol(symbol)         # Validate trading pair
bot.get_current_price(symbol)       # Get current market price
Order Placement
python
bot.place_market_order(symbol, side, quantity)
bot.place_limit_order(symbol, side, quantity, price)
bot.place_stop_limit_order(symbol, side, quantity, price, stop_price)
bot.place_oco_order(symbol, side, quantity, price, stop_price)
bot.place_grid_order(symbol, side, quantity, base_price, levels, percentage)
bot.place_twap_order(symbol, side, total_quantity, num_slices, interval)
Order Management
python
bot.get_open_orders(symbol=None)    # Get open orders
bot.get_order_status(symbol, order_id)  # Get specific order
bot.cancel_order(symbol, order_id)  # Cancel an order
History
python
bot.display_order_history()         # Display session orders
🎓 Learning Resources
Binance API Docs: https://binance-docs.github.io/apidocs/futures/

Python-Binance Docs: https://python-binance.readthedocs.io/

Trading Strategy Ideas: https://www.investopedia.com/

📄 License
This project is provided as-is for educational purposes. Use at your own risk.

⚠️ Disclaimer
This bot is for educational and testing purposes only. Use the Testnet environment extensively before considering any real trading. The authors are not responsible for any losses or damages resulting from the use of this software.

🤝 Contributing
Contributions are welcome! Feel free to:

Report bugs

Suggest improvements

Submit pull requests

Share your strategies

📞 Support
For issues or questions:

Check the Troubleshooting section

Review logs in trading_bot.log

Check Binance API documentation

Open an issue on GitHub

Happy Trading! 🚀