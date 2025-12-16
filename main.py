import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import hmac
import hashlib


# ==================== CONFIGURATION ====================
class Environment(Enum):
    """Environment configuration"""
    TESTNET = "testnet"
    MAINNET = "mainnet"


class OrderType(Enum):
    """Supported order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
    OCO = "OCO"
    GRID = "GRID"
    TWAP = "TWAP"


class OrderSide(Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


# ==================== LOGGING SETUP ====================
def setup_logging(log_file: str = "trading_bot.log") -> logging.Logger:
    """Configure logging with file and console output"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


# ==================== DATA CLASSES ====================
@dataclass
class OrderConfig:
    """Order configuration"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # Good Till Cancelled
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "timeInForce": self.time_in_force,
        }


# ==================== TRADING BOT CLASS ====================
class BinanceTradingBot:
    """
    Simplified Binance Trading Bot with support for multiple order types
    Uses Binance Futures Testnet for risk-free trading
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        environment: Environment = Environment.TESTNET
    ):
        """
        Initialize the trading bot

        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet (deprecated, use environment)
            environment: Trading environment (TESTNET or MAINNET)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet or environment == Environment.TESTNET
        self.environment = environment

        # Initialize Binance client
        try:
            self.client = Client(
                api_key=api_key,
                api_secret=api_secret,
                testnet=self.testnet
            )
            logger.info(f"✓ Connected to Binance {environment.value}")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Binance client: {str(e)}")
            raise

        # Order tracking
        self.orders: Dict[str, Dict] = {}
        self.order_history: List[Dict] = []

    def get_account_balance(self) -> Dict:
        """Get account balance information"""
        try:
            account = self.client.futures_account()
            logger.info(f"✓ Retrieved account info")
            
            balance_info = {
                "total_wallet_balance": float(account.get("totalWalletBalance", 0)),
                "available_balance": float(account.get("availableBalance", 0)),
                "used_balance": float(account.get("totalWalletBalance", 0)) - float(account.get("availableBalance", 0)),
                "margin_level": float(account.get("totalMaintMargin", 0)),
            }
            
            logger.debug(f"Account Balance: {json.dumps(balance_info, indent=2)}")
            return balance_info
        except BinanceAPIException as e:
            logger.error(f"✗ Binance API error: {e.status_code} - {e.message}")
            return {}
        except Exception as e:
            logger.error(f"✗ Error getting account balance: {str(e)}")
            return {}

    def validate_symbol(self, symbol: str) -> bool:
        """Validate if trading symbol exists"""
        try:
            # Remove USDT if present for clean symbol
            clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
            self.client.futures_exchange_info()
            logger.debug(f"✓ Symbol {clean_symbol} validated")
            return True
        except Exception as e:
            logger.error(f"✗ Symbol validation failed: {str(e)}")
            return False

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol"""
        try:
            clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
            ticker = self.client.futures_symbol_ticker(symbol=clean_symbol)
            price = float(ticker["price"])
            logger.debug(f"Current price for {clean_symbol}: {price}")
            return price
        except Exception as e:
            logger.error(f"✗ Error fetching price for {symbol}: {str(e)}")
            return None

    def place_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float
    ) -> Optional[Dict]:
        """
        Place a market order

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: BUY or SELL
            quantity: Order quantity

        Returns:
            Order details or None if failed
        """
        try:
            clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
            
            logger.info(f"📊 Placing {side.value} MARKET order - {clean_symbol} x {quantity}")
            
            order = self.client.futures_create_order(
                symbol=clean_symbol,
                side=side.value,
                type=OrderType.MARKET.value,
                quantity=quantity
            )

            self.orders[order["orderId"]] = order
            self.order_history.append({
                **order,
                "timestamp": datetime.now().isoformat(),
                "order_type": OrderType.MARKET.value
            })

            logger.info(f"✓ Market order placed - Order ID: {order['orderId']}")
            logger.debug(f"Order Details: {json.dumps(order, indent=2, default=str)}")
            
            return order

        except BinanceAPIException as e:
            logger.error(f"✗ Binance API error: {e.status_code} - {e.message}")
            return None
        except BinanceOrderException as e:
            logger.error(f"✗ Order error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"✗ Unexpected error placing market order: {str(e)}")
            return None

    def place_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        time_in_force: str = "GTC"
    ) -> Optional[Dict]:
        """
        Place a limit order

        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            price: Limit price
            time_in_force: GTC, IOC, FOK

        Returns:
            Order details or None if failed
        """
        try:
            clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
            
            logger.info(f"📊 Placing {side.value} LIMIT order - {clean_symbol} @ {price} x {quantity}")
            
            order = self.client.futures_create_order(
                symbol=clean_symbol,
                side=side.value,
                type=OrderType.LIMIT.value,
                timeInForce=time_in_force,
                quantity=quantity,
                price=price
            )

            self.orders[order["orderId"]] = order
            self.order_history.append({
                **order,
                "timestamp": datetime.now().isoformat(),
                "order_type": OrderType.LIMIT.value
            })

            logger.info(f"✓ Limit order placed - Order ID: {order['orderId']}")
            logger.debug(f"Order Details: {json.dumps(order, indent=2, default=str)}")
            
            return order

        except BinanceAPIException as e:
            logger.error(f"✗ Binance API error: {e.status_code} - {e.message}")
            return None
        except BinanceOrderException as e:
            logger.error(f"✗ Order error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"✗ Unexpected error placing limit order: {str(e)}")
            return None

    def place_stop_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        stop_price: float,
        time_in_force: str = "GTC"
    ) -> Optional[Dict]:
        """
        Place a Stop-Limit order

        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            price: Limit price
            stop_price: Trigger price
            time_in_force: GTC, IOC, FOK

        Returns:
            Order details or None if failed
        """
        try:
            clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
            
            logger.info(f"📊 Placing {side.value} STOP-LIMIT order - {clean_symbol}")
            logger.info(f"   Stop Price: {stop_price}, Limit Price: {price}, Quantity: {quantity}")
            
            order = self.client.futures_create_order(
                symbol=clean_symbol,
                side=side.value,
                type=OrderType.STOP_LIMIT.value,
                timeInForce=time_in_force,
                quantity=quantity,
                price=price,
                stopPrice=stop_price
            )

            self.orders[order["orderId"]] = order
            self.order_history.append({
                **order,
                "timestamp": datetime.now().isoformat(),
                "order_type": OrderType.STOP_LIMIT.value,
                "stop_price": stop_price
            })

            logger.info(f"✓ Stop-Limit order placed - Order ID: {order['orderId']}")
            logger.debug(f"Order Details: {json.dumps(order, indent=2, default=str)}")
            
            return order

        except BinanceAPIException as e:
            logger.error(f"✗ Binance API error: {e.status_code} - {e.message}")
            return None
        except BinanceOrderException as e:
            logger.error(f"✗ Order error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"✗ Unexpected error placing stop-limit order: {str(e)}")
            return None

    def place_oco_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        stop_price: float,
        stop_limit_price: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Place One-Cancels-Other (OCO) order
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            price: Profit-taking (limit) price
            stop_price: Stop loss trigger price
            stop_limit_price: Stop loss limit price (defaults to stop_price if not provided)

        Returns:
            Order details or None if failed
        """
        try:
            clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
            
            if stop_limit_price is None:
                stop_limit_price = stop_price
            
            logger.info(f"📊 Placing {side.value} OCO order - {clean_symbol}")
            logger.info(f"   Limit Price: {price}, Stop Price: {stop_price}, Stop Limit: {stop_limit_price}")
            
            order = self.client.futures_create_order(
                symbol=clean_symbol,
                side=side.value,
                type=OrderType.LIMIT.value,
                timeInForce="GTC",
                quantity=quantity,
                price=price,
                stopPrice=stop_price,
                stopLimitPrice=stop_limit_price,
                stopLimitTimeInForce="GTC"
            )

            self.orders[order["orderId"]] = order
            self.order_history.append({
                **order,
                "timestamp": datetime.now().isoformat(),
                "order_type": "OCO",
                "stop_price": stop_price
            })

            logger.info(f"✓ OCO order placed - Order ID: {order['orderId']}")
            logger.debug(f"Order Details: {json.dumps(order, indent=2, default=str)}")
            
            return order

        except BinanceAPIException as e:
            logger.error(f"✗ Binance API error: {e.status_code} - {e.message}")
            return None
        except Exception as e:
            logger.error(f"✗ Unexpected error placing OCO order: {str(e)}")
            return None

    def place_grid_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        base_price: float,
        grid_levels: int = 5,
        grid_percentage: float = 2.0
    ) -> List[Dict]:
        """
        Place Grid Trading Orders
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Total quantity to distribute
            base_price: Starting price
            grid_levels: Number of price levels
            grid_percentage: Percentage between levels

        Returns:
            List of placed orders
        """
        try:
            clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
            
            logger.info(f"📊 Placing {side.value} GRID orders - {clean_symbol}")
            logger.info(f"   Base Price: {base_price}, Levels: {grid_levels}, Spread: {grid_percentage}%")
            
            orders = []
            qty_per_level = quantity / grid_levels
            
            for level in range(grid_levels):
                # Calculate price for this level
                if side == OrderSide.BUY:
                    # Buy orders go down
                    price = base_price * (1 - (level * grid_percentage / 100))
                else:
                    # Sell orders go up
                    price = base_price * (1 + (level * grid_percentage / 100))
                
                price = float(Decimal(str(price)).quantize(Decimal('0.01'), rounding=ROUND_DOWN))
                
                logger.info(f"   Grid Level {level + 1}: {price} x {qty_per_level}")
                
                order = self.client.futures_create_order(
                    symbol=clean_symbol,
                    side=side.value,
                    type=OrderType.LIMIT.value,
                    timeInForce="GTC",
                    quantity=qty_per_level,
                    price=price
                )
                
                self.orders[order["orderId"]] = order
                self.order_history.append({
                    **order,
                    "timestamp": datetime.now().isoformat(),
                    "order_type": OrderType.GRID.value,
                    "grid_level": level + 1
                })
                
                orders.append(order)
                logger.debug(f"Grid order placed - Level {level + 1}, ID: {order['orderId']}")
            
            logger.info(f"✓ Grid orders placed - Total: {len(orders)} orders")
            return orders

        except Exception as e:
            logger.error(f"✗ Error placing grid orders: {str(e)}")
            return []

    def place_twap_order(
        self,
        symbol: str,
        side: OrderSide,
        total_quantity: float,
        num_slices: int = 5,
        time_interval: float = 60.0
    ) -> List[Dict]:
        """
        Place Time-Weighted Average Price (TWAP) orders
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            total_quantity: Total quantity to execute
            num_slices: Number of order slices
            time_interval: Seconds between each slice

        Returns:
            List of placed orders
        """
        try:
            clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
            
            logger.info(f"📊 Placing {side.value} TWAP orders - {clean_symbol}")
            logger.info(f"   Total: {total_quantity}, Slices: {num_slices}, Interval: {time_interval}s")
            
            orders = []
            qty_per_slice = total_quantity / num_slices
            
            for slice_num in range(num_slices):
                logger.info(f"   Executing slice {slice_num + 1}/{num_slices} ({qty_per_slice} units)")
                
                order = self.client.futures_create_order(
                    symbol=clean_symbol,
                    side=side.value,
                    type=OrderType.MARKET.value,
                    quantity=qty_per_slice
                )
                
                self.orders[order["orderId"]] = order
                self.order_history.append({
                    **order,
                    "timestamp": datetime.now().isoformat(),
                    "order_type": OrderType.TWAP.value,
                    "slice_number": slice_num + 1
                })
                
                orders.append(order)
                logger.info(f"✓ TWAP slice {slice_num + 1} executed - Order ID: {order['orderId']}")
                
                # Wait before next slice (except for the last one)
                if slice_num < num_slices - 1:
                    logger.info(f"⏱️  Waiting {time_interval}s before next slice...")
                    time.sleep(time_interval)
            
            logger.info(f"✓ TWAP orders completed - Total slices: {len(orders)}")
            return orders

        except Exception as e:
            logger.error(f"✗ Error placing TWAP orders: {str(e)}")
            return []

    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """
        Cancel an open order

        Args:
            symbol: Trading pair
            order_id: Order ID to cancel

        Returns:
            True if successful, False otherwise
        """
        try:
            clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
            
            logger.info(f"🗑️  Cancelling order - {clean_symbol} (ID: {order_id})")
            
            result = self.client.futures_cancel_order(
                symbol=clean_symbol,
                orderId=order_id
            )
            
            logger.info(f"✓ Order cancelled successfully")
            logger.debug(f"Cancellation details: {json.dumps(result, indent=2, default=str)}")
            
            return True

        except BinanceAPIException as e:
            logger.error(f"✗ Binance API error: {e.status_code} - {e.message}")
            return False
        except Exception as e:
            logger.error(f"✗ Error cancelling order: {str(e)}")
            return False

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders"""
        try:
            if symbol:
                clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
                orders = self.client.futures_get_open_orders(symbol=clean_symbol)
                logger.info(f"✓ Retrieved {len(orders)} open orders for {clean_symbol}")
            else:
                orders = self.client.futures_get_open_orders()
                logger.info(f"✓ Retrieved {len(orders)} total open orders")
            
            logger.debug(f"Open Orders: {json.dumps(orders, indent=2, default=str)}")
            return orders

        except Exception as e:
            logger.error(f"✗ Error fetching open orders: {str(e)}")
            return []

    def get_order_status(self, symbol: str, order_id: int) -> Optional[Dict]:
        """Get specific order status"""
        try:
            clean_symbol = symbol.replace("USDT", "").upper() + "USDT"
            
            order = self.client.futures_get_order(
                symbol=clean_symbol,
                orderId=order_id
            )
            
            logger.info(f"✓ Retrieved order status - ID: {order_id}")
            logger.debug(f"Order Status: {json.dumps(order, indent=2, default=str)}")
            
            return order

        except Exception as e:
            logger.error(f"✗ Error fetching order status: {str(e)}")
            return None

    def display_order_history(self):
        """Display formatted order history"""
        if not self.order_history:
            print("\n❌ No orders in history\n")
            return
        
        print("\n" + "="*100)
        print("ORDER HISTORY")
        print("="*100)
        
        for idx, order in enumerate(self.order_history, 1):
            print(f"\n📋 Order #{idx}")
            print(f"   Order ID: {order.get('orderId')}")
            print(f"   Symbol: {order.get('symbol')}")
            print(f"   Type: {order.get('order_type')}")
            print(f"   Side: {order.get('side')}")
            print(f"   Quantity: {order.get('origQty')}")
            print(f"   Price: {order.get('price', 'Market')}")
            if 'stop_price' in order:
                print(f"   Stop Price: {order['stop_price']}")
            print(f"   Status: {order.get('status')}")
            print(f"   Timestamp: {order.get('timestamp')}")
        
        print("\n" + "="*100 + "\n")


# ==================== CLI INTERFACE ====================
class TradingBotCLI:
    """Command-line interface for the trading bot"""

    def __init__(self, bot: BinanceTradingBot):
        self.bot = bot

    def display_menu(self):
        """Display main menu"""
        print("\n" + "="*60)
        print("🤖 BINANCE TRADING BOT - TESTNET")
        print("="*60)
        print("\n1. Account & Balance")
        print("   [1.1] Check Account Balance")
        print("   [1.2] Check Open Orders")
        print("\n2. Place Orders")
        print("   [2.1] Market Order")
        print("   [2.2] Limit Order")
        print("   [2.3] Stop-Limit Order")
        print("   [2.4] OCO Order")
        print("   [2.5] Grid Orders")
        print("   [2.6] TWAP Orders")
        print("\n3. Manage Orders")
        print("   [3.1] Get Order Status")
        print("   [3.2] Cancel Order")
        print("\n4. View History")
        print("   [4.1] Display Order History")
        print("\n5. Exit")
        print("\n" + "="*60)

    def get_input(self, prompt: str, input_type=str, required=True):
        """Get validated user input"""
        while True:
            try:
                value = input(prompt).strip()
                
                if not value and required:
                    print("❌ This field is required")
                    continue
                
                if input_type == float:
                    return float(value)
                elif input_type == int:
                    return int(value)
                elif input_type == str:
                    return value
                
                return value
            except ValueError:
                print(f"❌ Invalid input. Please enter a valid {input_type.__name__}")

    def run(self):
        """Run the CLI"""
        print("\n✅ Trading Bot initialized successfully!")
        
        while True:
            self.display_menu()
            choice = self.get_input("Enter your choice: ")
            
            if choice == "1.1":
                self.handle_check_balance()
            elif choice == "1.2":
                self.handle_check_orders()
            elif choice == "2.1":
                self.handle_market_order()
            elif choice == "2.2":
                self.handle_limit_order()
            elif choice == "2.3":
                self.handle_stop_limit_order()
            elif choice == "2.4":
                self.handle_oco_order()
            elif choice == "2.5":
                self.handle_grid_order()
            elif choice == "2.6":
                self.handle_twap_order()
            elif choice == "3.1":
                self.handle_order_status()
            elif choice == "3.2":
                self.handle_cancel_order()
            elif choice == "4.1":
                self.bot.display_order_history()
            elif choice == "5":
                print("\n👋 Goodbye!\n")
                break
            else:
                print("❌ Invalid choice. Please try again.")

    def handle_check_balance(self):
        """Handle balance check"""
        print("\n" + "-"*60)
        balance = self.bot.get_account_balance()
        if balance:
            print("\n💰 Account Balance:")
            print(f"   Total Wallet Balance: ${balance['total_wallet_balance']:.2f}")
            print(f"   Available Balance: ${balance['available_balance']:.2f}")
            print(f"   Used Balance: ${balance['used_balance']:.2f}")
            print(f"   Margin Level: {balance['margin_level']:.4f}")
        else:
            print("❌ Failed to retrieve balance")
        print("-"*60 + "\n")

    def handle_check_orders(self):
        """Handle checking open orders"""
        print("\n" + "-"*60)
        symbol = self.get_input("Enter symbol (e.g., BTCUSDT) [leave blank for all]: ", required=False)
        
        orders = self.bot.get_open_orders(symbol if symbol else None)
        
        if not orders:
            print("No open orders found")
        else:
            print(f"\n📊 Open Orders ({len(orders)}):")
            for idx, order in enumerate(orders, 1):
                print(f"\n   {idx}. {order['symbol']} - {order['side']}")
                print(f"      Type: {order['type']}")
                print(f"      Quantity: {order['origQty']}")
                print(f"      Price: {order.get('price', 'N/A')}")
                print(f"      Status: {order['status']}")
        
        print("-"*60 + "\n")

    def handle_market_order(self):
        """Handle market order placement"""
        print("\n" + "-"*60)
        print("📊 Market Order")
        
        symbol = self.get_input("Symbol (e.g., BTCUSDT): ").upper()
        side_input = self.get_input("Side (BUY/SELL): ").upper()
        quantity = self.get_input("Quantity: ", float)
        
        side = OrderSide.BUY if side_input == "BUY" else OrderSide.SELL
        
        result = self.bot.place_market_order(symbol, side, quantity)
        if result:
            print(f"\n✅ Market order placed successfully!")
            print(f"   Order ID: {result['orderId']}")
            print(f"   Status: {result['status']}")
        else:
            print("\n❌ Failed to place market order")
        
        print("-"*60 + "\n")

    def handle_limit_order(self):
        """Handle limit order placement"""
        print("\n" + "-"*60)
        print("📊 Limit Order")
        
        symbol = self.get_input("Symbol (e.g., BTCUSDT): ").upper()
        side_input = self.get_input("Side (BUY/SELL): ").upper()
        quantity = self.get_input("Quantity: ", float)
        price = self.get_input("Price: ", float)
        
        side = OrderSide.BUY if side_input == "BUY" else OrderSide.SELL
        
        result = self.bot.place_limit_order(symbol, side, quantity, price)
        if result:
            print(f"\n✅ Limit order placed successfully!")
            print(f"   Order ID: {result['orderId']}")
            print(f"   Status: {result['status']}")
        else:
            print("\n❌ Failed to place limit order")
        
        print("-"*60 + "\n")

    def handle_stop_limit_order(self):
        """Handle stop-limit order placement"""
        print("\n" + "-"*60)
        print("📊 Stop-Limit Order")
        
        symbol = self.get_input("Symbol (e.g., BTCUSDT): ").upper()
        side_input = self.get_input("Side (BUY/SELL): ").upper()
        quantity = self.get_input("Quantity: ", float)
        stop_price = self.get_input("Stop Price: ", float)
        limit_price = self.get_input("Limit Price: ", float)
        
        side = OrderSide.BUY if side_input == "BUY" else OrderSide.SELL
        
        result = self.bot.place_stop_limit_order(symbol, side, quantity, limit_price, stop_price)
        if result:
            print(f"\n✅ Stop-Limit order placed successfully!")
            print(f"   Order ID: {result['orderId']}")
            print(f"   Status: {result['status']}")
        else:
            print("\n❌ Failed to place stop-limit order")
        
        print("-"*60 + "\n")

    def handle_oco_order(self):
        """Handle OCO order placement"""
        print("\n" + "-"*60)
        print("📊 OCO (One-Cancels-Other) Order")
        print("   (Limit order + Stop-Loss order)")
        
        symbol = self.get_input("Symbol (e.g., BTCUSDT): ").upper()
        side_input = self.get_input("Side (BUY/SELL): ").upper()
        quantity = self.get_input("Quantity: ", float)
        limit_price = self.get_input("Limit Price (Profit target): ", float)
        stop_price = self.get_input("Stop Price (Stop loss): ", float)
        
        side = OrderSide.BUY if side_input == "BUY" else OrderSide.SELL
        
        result = self.bot.place_oco_order(symbol, side, quantity, limit_price, stop_price)
        if result:
            print(f"\n✅ OCO order placed successfully!")
            print(f"   Order ID: {result['orderId']}")
            print(f"   Status: {result['status']}")
        else:
            print("\n❌ Failed to place OCO order")
        
        print("-"*60 + "\n")

    def handle_grid_order(self):
        """Handle grid order placement"""
        print("\n" + "-"*60)
        print("📊 Grid Trading Orders")
        
        symbol = self.get_input("Symbol (e.g., BTCUSDT): ").upper()
        side_input = self.get_input("Side (BUY/SELL): ").upper()
        total_qty = self.get_input("Total Quantity: ", float)
        base_price = self.get_input("Base Price: ", float)
        grid_levels = self.get_input("Grid Levels (default 5): ", int)
        grid_percent = self.get_input("Grid Percentage (default 2.0): ", float)
        
        side = OrderSide.BUY if side_input == "BUY" else OrderSide.SELL
        
        results = self.bot.place_grid_order(symbol, side, total_qty, base_price, grid_levels, grid_percent)
        
        if results:
            print(f"\n✅ Grid orders placed successfully!")
            print(f"   Total orders: {len(results)}")
            for idx, order in enumerate(results, 1):
                print(f"   Order {idx}: ID {order['orderId']} - Status: {order['status']}")
        else:
            print("\n❌ Failed to place grid orders")
        
        print("-"*60 + "\n")

    def handle_twap_order(self):
        """Handle TWAP order placement"""
        print("\n" + "-"*60)
        print("📊 TWAP (Time-Weighted Average Price) Orders")
        
        symbol = self.get_input("Symbol (e.g., BTCUSDT): ").upper()
        side_input = self.get_input("Side (BUY/SELL): ").upper()
        total_qty = self.get_input("Total Quantity: ", float)
        slices = self.get_input("Number of Slices (default 5): ", int)
        interval = self.get_input("Interval between slices in seconds (default 60): ", float)
        
        side = OrderSide.BUY if side_input == "BUY" else OrderSide.SELL
        
        results = self.bot.place_twap_order(symbol, side, total_qty, slices, interval)
        
        if results:
            print(f"\n✅ TWAP orders completed successfully!")
            print(f"   Total slices: {len(results)}")
            for idx, order in enumerate(results, 1):
                print(f"   Slice {idx}: ID {order['orderId']} - Status: {order['status']}")
        else:
            print("\n❌ Failed to place TWAP orders")
        
        print("-"*60 + "\n")

    def handle_order_status(self):
        """Handle getting order status"""
        print("\n" + "-"*60)
        
        symbol = self.get_input("Symbol (e.g., BTCUSDT): ").upper()
        order_id = self.get_input("Order ID: ", int)
        
        result = self.bot.get_order_status(symbol, order_id)
        
        if result:
            print(f"\n📋 Order Status:")
            print(f"   Order ID: {result['orderId']}")
            print(f"   Symbol: {result['symbol']}")
            print(f"   Side: {result['side']}")
            print(f"   Type: {result['type']}")
            print(f"   Quantity: {result['origQty']}")
            print(f"   Price: {result.get('price', 'N/A')}")
            print(f"   Status: {result['status']}")
            print(f"   Executed: {result['executedQty']}")
        else:
            print("\n❌ Failed to get order status")
        
        print("-"*60 + "\n")

    def handle_cancel_order(self):
        """Handle order cancellation"""
        print("\n" + "-"*60)
        
        symbol = self.get_input("Symbol (e.g., BTCUSDT): ").upper()
        order_id = self.get_input("Order ID: ", int)
        
        confirm = self.get_input(f"Cancel order {order_id}? (yes/no): ").lower()
        
        if confirm == "yes":
            result = self.bot.cancel_order(symbol, order_id)
            if result:
                print("\n✅ Order cancelled successfully!")
            else:
                print("\n❌ Failed to cancel order")
        else:
            print("\n⏭️  Cancellation aborted")
        
        print("-"*60 + "\n")


# ==================== MAIN ====================
def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🚀 BINANCE TRADING BOT SETUP")
    print("="*60 + "\n")
    
    print("📝 Instructions:")
    print("1. Go to https://testnet.binancefuture.com")
    print("2. Sign up or login")
    print("3. Navigate to API Management")
    print("4. Create new API key with Futures permissions")
    print("5. Keep your API key and secret safe!")
    print("\n")
    
    api_key = input("Enter your Binance Testnet API Key: ").strip()
    api_secret = input("Enter your Binance Testnet API Secret: ").strip()
    
    if not api_key or not api_secret:
        print("\n❌ API credentials are required!")
        sys.exit(1)
    
    print("\n⏳ Initializing bot...")
    
    try:
        # Initialize bot
        bot = BinanceTradingBot(
            api_key=api_key,
            api_secret=api_secret,
            testnet=True,
            environment=Environment.TESTNET
        )
        
        # Start CLI
        cli = TradingBotCLI(bot)
        cli.run()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()