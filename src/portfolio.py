from typing import Dict, Optional, List
from collections import defaultdict
from src.events import SignalEvent, OrderEvent, FillEvent, MarketEvent
import pandas as pd
from datetime import datetime

class Portfolio:
    """
    Handles positions and cash management.
    Generates Orders from Signals and updates state from Fills.
    Tracks equity curve history.
    """
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        self.holdings: Dict[str, int] = defaultdict(int) # Symbol -> Quantity
        self.current_value = initial_capital
        
        # History tracking
        self.history: List[Dict] = []
        self.latest_prices: Dict[str, float] = {}

    def update_market_event(self, event: MarketEvent):
        """
        Update latest prices and record equity curve point.
        """
        self.latest_prices[event.symbol] = event.price
        self._record_equity(event.time)

    def _record_equity(self, timestamp: datetime):
        """
        Calculates total equity (cash + open positions) and appends to history.
        """
        # Calculate market value of holdings
        holdings_value = 0.0
        for symbol, qty in self.holdings.items():
            price = self.latest_prices.get(symbol, 0.0)
            holdings_value += (qty * price)
            
        total_equity = self.current_cash + holdings_value
        
        self.history.append({
            'datetime': timestamp,
            'cash': self.current_cash,
            'equity': total_equity,
            'holdings_value': holdings_value
        })

    def update_fill(self, event: FillEvent):
        """
        Updates portfolio state based on a FillEvent.
        """
        fill_dir = 1 if event.direction == 'BUY' else -1
        cash_delta = event.quantity * event.price * fill_dir
        
        self.current_cash -= (cash_delta + event.commission)
        self.holdings[event.symbol] += (event.quantity * fill_dir)
        
        # Note: We could record equity here too, but usually done on MarketEvent (close of bar)
        
    def create_order(self, event: SignalEvent) -> Optional[OrderEvent]:
        """
        Converts a SignalEvent into an OrderEvent.
        Basic risk management: For now, fixed quantity logic allows buying.
        """
        if event.signal_type == 'LONG':
            # Simplified sizing: Buy 10 shares
            quantity = 10 
            return OrderEvent(
                time=event.time,
                symbol=event.symbol,
                order_type='MKT',
                quantity=quantity,
                direction='BUY'
            )
        elif event.signal_type == 'EXIT':
            # Close position if exists
            current_qty = self.holdings.get(event.symbol, 0)
            if current_qty > 0:
                return OrderEvent(
                    time=event.time,
                    symbol=event.symbol,
                    order_type='MKT',
                    quantity=current_qty,
                    direction='SELL'
                )
        return None
