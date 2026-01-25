from collections import deque
from typing import Optional
from src.events import Event, MarketEvent

class BacktestEngine:
    """
    The core event-driven execution engine.
    It manages the event queue and dispatches events to the appropriate components.
    """
    def __init__(self, data_handler=None, strategy=None):
        self.queue = deque()
        self.data_handler = data_handler
        self.strategy = strategy
        self.is_running = False
        self.processed_events = [] # Store processed events for State Verification

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
        print("Starting Backtest Engine...")
        
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
        print("Backtest Engine stopped.")

    def _process_event(self, event: Event):
        """
        Dispatches the event to the appropriate handler.
        """
        # Store event for verification and logging
        self.processed_events.append(event)
        
        # Dispatch to Strategy
        if isinstance(event, MarketEvent):
            if self.strategy:
                signal = self.strategy.calculate_signals(event)
                if signal:
                    self.queue.append(signal)
