import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Optional, List
from collections import defaultdict
from src.events import SignalEvent, OrderEvent, FillEvent, MarketEvent
from src.config import INITIAL_CAPITAL, COMMISSION_RATE, DEFAULT_RISK_PER_TRADE

logger = logging.getLogger(__name__)


class Portfolio:
    """
    Handles positions and cash management.
    Generates Orders from Signals and updates state from Fills.
    Tracks equity curve history.
    """

    def __init__(
        self,
        initial_capital: float = INITIAL_CAPITAL,
        commission_rate: float = COMMISSION_RATE,
        risk_per_trade: float = DEFAULT_RISK_PER_TRADE,
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.risk_per_trade = risk_per_trade
        self.current_cash = initial_capital
        self.holdings: Dict[str, int] = defaultdict(int)  # Symbol -> Quantity
        self.current_value = initial_capital

        # History tracking
        self.history: List[Dict] = []
        self.latest_prices: Dict[str, float] = {}

    def update_market_event(self, event: MarketEvent):
        """
        Update latest prices and record equity curve point.
        """
        self.latest_prices[event.symbol] = event.price
        self._record_equity(event.time, event.price)

    def _record_equity(self, timestamp: datetime, price: float = None):
        """
        Calculates total equity (cash + open positions) and appends to history.
        """
        # Calculate market value of holdings
        holdings_value = 0.0
        for symbol, qty in self.holdings.items():
            if qty == 0:
                continue
            p = self.latest_prices.get(symbol)
            if p is None:
                logger.warning(
                    f"No latest price for '{symbol}' (qty={qty}) during equity recording. "
                    "Position valued at $0, equity may be understated."
                )
                p = 0.0
            holdings_value += qty * p

        total_equity = self.current_cash + holdings_value

        self.history.append(
            {
                "datetime": timestamp,
                "cash": self.current_cash,
                "equity": total_equity,
                "holdings_value": holdings_value,
                "price": price,
            }
        )

    def update_fill(self, event: FillEvent):
        """
        Updates portfolio state based on a FillEvent.
        """
        fill_dir = 1 if event.direction == "BUY" else -1
        cash_delta = event.quantity * event.price * fill_dir
        commission = (
            event.commission
            if event.commission > 0
            else (abs(cash_delta) * self.commission_rate)
        )

        self.current_cash -= cash_delta + commission
        self.holdings[event.symbol] += event.quantity * fill_dir

        logger.info(
            f"FILL: {event.direction} {event.quantity} {event.symbol} @ {event.price}. Cash Residue: {self.current_cash:.2f}"
        )

        # Note: We could record equity here too, but usually done on MarketEvent (close of bar)

    def create_order(
        self, event: SignalEvent, risk_per_trade: float = None
    ) -> Optional[OrderEvent]:
        """
        Converts a SignalEvent into an OrderEvent.
        Implements risk-based position sizing:
        quantity = (Equity * Risk%) / current_price
        """
        if risk_per_trade is None:
            risk_per_trade = self.risk_per_trade
        if event.signal_type == "LONG":
            price = self.latest_prices.get(event.symbol)
            if not price:
                logger.warning(
                    f"No price available for {event.symbol}, cannot size position."
                )
                return None

            # Risk-based sizing
            equity = self.current_cash
            for s, qty in self.holdings.items():
                if qty == 0:
                    continue
                p = self.latest_prices.get(s)
                if p is None:
                    logger.warning(
                        f"No latest price for holding '{s}' (qty={qty}) during position sizing. "
                        "Position valued at $0, equity may be understated."
                    )
                    p = 0.0
                equity += qty * p
            risk_amount = equity * risk_per_trade
            quantity = int(risk_amount / price)

            if quantity <= 0:
                logger.warning(
                    f"Sized quantity is 0 for {event.symbol}. Risk amount: {risk_amount:.2f}"
                )
                return None

            return OrderEvent(
                time=event.time,
                symbol=event.symbol,
                order_type="MKT",
                quantity=quantity,
                direction="BUY",
            )
        elif event.signal_type == "SHORT":
            price = self.latest_prices.get(event.symbol)
            if not price:
                logger.warning(
                    f"No price available for {event.symbol}, cannot size short position."
                )
                return None

            equity = self.current_cash
            for s, qty in self.holdings.items():
                if qty == 0:
                    continue
                p = self.latest_prices.get(s)
                if p is None:
                    logger.warning(
                        f"No latest price for holding '{s}' (qty={qty}) during short sizing. "
                        "Position valued at $0, equity may be understated."
                    )
                    p = 0.0
                equity += qty * p

            risk_amount = equity * risk_per_trade
            quantity = int(risk_amount / price)

            if quantity <= 0:
                logger.warning(
                    f"Sized short quantity is 0 for {event.symbol}. Risk amount: {risk_amount:.2f}"
                )
                return None

            return OrderEvent(
                time=event.time,
                symbol=event.symbol,
                order_type="MKT",
                quantity=quantity,
                direction="SELL",
            )

        elif event.signal_type == "EXIT":
            current_qty = self.holdings.get(event.symbol, 0)
            if current_qty > 0:
                # Long position: sell to close
                return OrderEvent(
                    time=event.time,
                    symbol=event.symbol,
                    order_type="MKT",
                    quantity=current_qty,
                    direction="SELL",
                )
            elif current_qty < 0:
                # Short position: buy to cover
                return OrderEvent(
                    time=event.time,
                    symbol=event.symbol,
                    order_type="MKT",
                    quantity=abs(current_qty),
                    direction="BUY",
                )
        return None
