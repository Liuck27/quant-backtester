"""
Tests for the SSE /stream/{job_id} endpoint and the progress_callback
plumbing through BacktestEngine.
"""

import json
import queue
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.jobs import job_manager, JobStatus, BacktestJob
from src.engine import BacktestEngine
from src.events import MarketEvent, FillEvent
from src.portfolio import Portfolio


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_job_manager():
    job_manager.jobs.clear()
    job_manager.futures.clear()
    yield


# ============================================================
# Engine callback unit tests
# ============================================================


class TestEngineProgressCallback:
    def test_callback_called_on_market_event(self):
        """Engine should invoke progress_callback with an equity event after each MarketEvent."""
        received = []
        engine = BacktestEngine(progress_callback=received.append)

        portfolio = MagicMock()
        portfolio.history = [
            {"datetime": datetime(2023, 1, 1), "equity": 100000.0, "cash": 100000.0}
        ]
        engine.portfolio = portfolio

        event = MarketEvent(time=datetime(2023, 1, 1), symbol="AAPL", price=150.0, volume=1000)
        engine._process_event(event)

        assert len(received) == 1
        assert received[0]["type"] == "equity"
        assert received[0]["equity"] == 100000.0
        assert received[0]["cash"] == 100000.0
        assert "time" in received[0]

    def test_callback_called_on_fill_event(self):
        """Engine should invoke progress_callback with a fill event after each FillEvent."""
        received = []
        engine = BacktestEngine(progress_callback=received.append)

        portfolio = MagicMock()
        engine.portfolio = portfolio

        event = FillEvent(
            time=datetime(2023, 1, 2),
            symbol="AAPL",
            quantity=10,
            price=150.0,
            direction="BUY",
        )
        engine._process_event(event)

        assert len(received) == 1
        assert received[0]["type"] == "fill"
        assert received[0]["symbol"] == "AAPL"
        assert received[0]["direction"] == "BUY"
        assert received[0]["quantity"] == 10
        assert received[0]["price"] == 150.0

    def test_no_callback_does_not_raise(self):
        """Engine without a callback should run without error."""
        engine = BacktestEngine()
        portfolio = MagicMock()
        portfolio.history = [
            {"datetime": datetime(2023, 1, 1), "equity": 100000.0, "cash": 100000.0}
        ]
        engine.portfolio = portfolio

        event = MarketEvent(time=datetime(2023, 1, 1), symbol="AAPL", price=150.0, volume=1000)
        engine._process_event(event)  # should not raise

    def test_callback_not_called_without_portfolio(self):
        """Engine with callback but no portfolio should not emit equity events."""
        received = []
        engine = BacktestEngine(progress_callback=received.append)
        # no portfolio set

        event = MarketEvent(time=datetime(2023, 1, 1), symbol="AAPL", price=150.0, volume=1000)
        engine._process_event(event)

        assert received == []


# ============================================================
# SSE endpoint tests
# ============================================================


def _make_running_job() -> BacktestJob:
    """Helper: create a job and mark it as running."""
    job = job_manager.create_job(
        symbol="AAPL",
        start_date="2023-01-01",
        end_date="2023-06-01",
        strategy="ma_crossover",
        parameters={},
    )
    job.status = JobStatus.RUNNING
    return job


def _parse_sse_lines(raw_lines) -> list[dict]:
    """Parse `data: {...}` lines from an SSE stream into a list of dicts."""
    events = []
    for line in raw_lines:
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


class TestSSEEndpoint:
    def test_stream_returns_404_for_unknown_job(self, client):
        response = client.get("/stream/nonexistent-id")
        assert response.status_code == 404

    def test_stream_yields_equity_and_done_events(self, client):
        """Stream should yield equity events followed by a done event."""
        job = _make_running_job()

        def enqueue():
            time.sleep(0.05)
            job.event_queue.put({"type": "equity", "time": "2023-01-01T00:00:00", "equity": 100000.0, "cash": 100000.0})
            job.event_queue.put({"type": "equity", "time": "2023-01-02T00:00:00", "equity": 101000.0, "cash": 100000.0})
            job.event_queue.put({"type": "done", "metrics": {"total_return": 1.0}, "final_equity": 101000.0})

        t = threading.Thread(target=enqueue)
        t.start()

        lines = []
        with client.stream("GET", f"/stream/{job.job_id}") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            for line in response.iter_lines():
                lines.append(line)
                if "done" in line:
                    break

        t.join()
        events = _parse_sse_lines(lines)

        equity_events = [e for e in events if e["type"] == "equity"]
        done_events = [e for e in events if e["type"] == "done"]

        assert len(equity_events) == 2
        assert equity_events[0]["equity"] == 100000.0
        assert equity_events[1]["equity"] == 101000.0
        assert len(done_events) == 1
        assert done_events[0]["final_equity"] == 101000.0

    def test_stream_yields_fill_events(self, client):
        """Stream should yield fill events for trades."""
        job = _make_running_job()

        def enqueue():
            time.sleep(0.05)
            job.event_queue.put({"type": "fill", "time": "2023-01-02T00:00:00", "symbol": "AAPL", "direction": "BUY", "quantity": 10, "price": 150.0})
            job.event_queue.put({"type": "done", "metrics": {}, "final_equity": 100000.0})

        t = threading.Thread(target=enqueue)
        t.start()

        lines = []
        with client.stream("GET", f"/stream/{job.job_id}") as response:
            for line in response.iter_lines():
                lines.append(line)
                if "done" in line:
                    break

        t.join()
        events = _parse_sse_lines(lines)

        fill_events = [e for e in events if e["type"] == "fill"]
        assert len(fill_events) == 1
        assert fill_events[0]["symbol"] == "AAPL"
        assert fill_events[0]["direction"] == "BUY"

    def test_stream_terminates_on_error_event(self, client):
        """Stream should terminate cleanly when an error event is emitted."""
        job = _make_running_job()

        def enqueue():
            time.sleep(0.05)
            job.event_queue.put({"type": "error", "message": "Data fetch failed"})

        t = threading.Thread(target=enqueue)
        t.start()

        lines = []
        with client.stream("GET", f"/stream/{job.job_id}") as response:
            for line in response.iter_lines():
                lines.append(line)
                if "error" in line:
                    break

        t.join()
        events = _parse_sse_lines(lines)

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert error_events[0]["message"] == "Data fetch failed"

    def test_stream_content_type_header(self, client):
        """Response must have the correct SSE content-type."""
        job = _make_running_job()

        def enqueue():
            time.sleep(0.05)
            job.event_queue.put({"type": "done", "metrics": {}, "final_equity": 100000.0})

        t = threading.Thread(target=enqueue)
        t.start()

        with client.stream("GET", f"/stream/{job.job_id}") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            for line in response.iter_lines():
                if "done" in line:
                    break

        t.join()
