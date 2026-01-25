from abc import ABC, abstractmethod
from typing import Optional
from src.events import MarketEvent, SignalEvent

class Strategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    Apps logic to MarketEvents to generate SignalEvents.
    """
    
    @abstractmethod
    def calculate_signals(self, event: MarketEvent) -> Optional[SignalEvent]:
        """
        Calculates signals based on market data.
        
        Args:
            event (MarketEvent): The latest market data event.
            
        Returns:
            Optional[SignalEvent]: A signal event if generated, else None.
        """
        pass

class BuyAndHoldStrategy(Strategy):
    """
    Naive strategy that generates a LONG signal on the first received bar 
    and then does nothing.
    """
    def __init__(self):
        self.bought = False

    def calculate_signals(self, event: MarketEvent) -> Optional[SignalEvent]:
        if not isinstance(event, MarketEvent):
            return None
            
        if not self.bought:
            self.bought = True
            return SignalEvent(
                time=event.time,
                symbol=event.symbol,
                signal_type="LONG"
            )
        return None
