import logging
from collections import deque
from typing import Optional
from src.events import Event, MarketEvent, SignalEvent, OrderEvent, FillEvent
from src.config import setup_logging, SLIPPAGE_RATE

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    The core event-driven execution engine.
    It manages the event queue and dispatches events to the appropriate components.
    """

    def __init__(self, data_handler=None, strategy=None, portfolio=None, progress_callback=None, slippage_rate=SLIPPAGE_RATE):
        setup_logging()
        self.queue = deque()
        self.data_handler = data_handler
        self.strategy = strategy
        self.portfolio = portfolio
        self.progress_callback = progress_callback
        self.slippage_rate = slippage_rate
        self.is_running = False
        self.processed_events = []  # Store processed events for State Verification

        # In a real system, we'd have a separate ExecutionHandler
        self.latest_prices = {}

    def put(self, event: Event):
        """
        Puts an event into the queue.

        Args:
            event (Event): The event to add to the queue.
        """
        self.queue.append(event)

    def run(self):
        """
        Main execution loop.
        Loops while there is still data in the handler or events in the queue.
        """
        self.is_running = True
        logger.info("Starting Backtest Engine...")

        while True:
            # 1. Update Data (if queue is empty, get more data)
            if len(self.queue) == 0:
                if self.data_handler and self.data_handler.continue_backtest:
                    event = self.data_handler.update_bars()
                    if event:
                        self.queue.append(event)
                elif self.data_handler and not self.data_handler.continue_backtest:
                    # Data finished and queue empty
                    break
                elif not self.data_handler and len(self.queue) == 0:
                    # No data handler and empty queue
                    break

            # 2. Process Queue
            if len(self.queue) > 0:
                event = self.queue.popleft()
                self._process_event(event)

        self.is_running = False
        logger.info("Backtest Engine stopped.")

    def _process_event(self, event: Event):
        """
        Dispatches the event to the appropriate handler.
        """
        # Store event for verification and logging
        self.processed_events.append(event)

        # 1. MarketEvent -> Strategy & Portfolio
        if isinstance(event, MarketEvent):
            self.latest_prices[event.symbol] = (
                event.price
            )  # Keep track of price for execution

            # Update Portfolio with latest price (Mark to Market)
            if self.portfolio:
                self.portfolio.update_market_event(event)
                if self.progress_callback and self.portfolio.history:
                    snap = self.portfolio.history[-1]
                    self.progress_callback({
                        "type": "equity",
                        "time": snap["datetime"].isoformat() if hasattr(snap["datetime"], "isoformat") else str(snap["datetime"]),
                        "equity": snap["equity"],
                        "cash": snap["cash"],
                        "price": event.price,
                    })

            if self.strategy:
                signal = self.strategy.calculate_signals(event)
                if signal:
                    self.queue.append(signal)

        # 2. SignalEvent -> Portfolio -> OrderEvent
        elif isinstance(event, SignalEvent):
            if self.portfolio:
                order = self.portfolio.create_order(event)
                if order:
                    self.queue.append(order)

        # 3. OrderEvent -> Simulated Execution -> FillEvent
        elif isinstance(event, OrderEvent):
            # Simplified Execution: Fill immediately at latest known price with slippage
            # In a real system, this would go to ExecutionHandler
            base_price = self.latest_prices.get(event.symbol, 0.0)
            if base_price > 0:
                # Apply slippage: BUY pays more, SELL receives less
                if event.direction == "BUY":
                    fill_price = base_price * (1 + self.slippage_rate)
                else:  # SELL
                    fill_price = base_price * (1 - self.slippage_rate)

                fill = FillEvent(
                    time=event.time,
                    symbol=event.symbol,
                    quantity=event.quantity,
                    price=fill_price,
                    direction=event.direction,
                )
                self.queue.append(fill)

        # 4. FillEvent -> Portfolio (Update holdings)
        elif isinstance(event, FillEvent):
            if self.portfolio:
                self.portfolio.update_fill(event)
            if self.progress_callback:
                self.progress_callback({
                    "type": "fill",
                    "time": event.time.isoformat() if hasattr(event.time, "isoformat") else str(event.time),
                    "symbol": event.symbol,
                    "direction": event.direction,
                    "quantity": event.quantity,
                    "price": event.price,
                })
