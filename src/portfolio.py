from typing import Dict, Optional
from collections import defaultdict
from src.events import SignalEvent, OrderEvent, FillEvent

class Portfolio:
    """
    Handles positions and cash management.
    Generates Orders from Signals and updates state from Fills.
    """
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        self.holdings: Dict[str, int] = defaultdict(int) # Symbol -> Quantity
        self.current_value = initial_capital
        
    def update_fill(self, event: FillEvent):
        """
        Updates portfolio state based on a FillEvent.
        """
        fill_dir = 1 if event.direction == 'BUY' else -1
        cash_delta = event.quantity * event.price * fill_dir
        
        self.current_cash -= (cash_delta + event.commission)
        self.holdings[event.symbol] += (event.quantity * fill_dir)
        
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
