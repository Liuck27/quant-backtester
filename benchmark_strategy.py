import time
import random
from datetime import datetime
from src.events import MarketEvent
from src.strategy import CppMovingAverageCrossStrategy, MovingAverageCrossStrategy


def benchmark():
    num_events = 100_000
    prices = [100.0 + random.uniform(-1, 1) for _ in range(num_events)]
    events = [MarketEvent(datetime.now(), "BENCH", p, 100) for p in prices]

    print(f"Benchmarking with {num_events} events...")

    # Python Benchmark
    py_strategy = MovingAverageCrossStrategy(short_window=50, long_window=200)
    start_time = time.time()
    for e in events:
        py_strategy.calculate_signals(e)
    py_duration = time.time() - start_time
    print(f"Python Implementation: {py_duration:.4f} seconds")

    # C++ Benchmark
    if CppMovingAverageCrossStrategy is None:
        print("C++ Implementation not available (Import Failed).")
    else:
        try:
            cpp_strategy = CppMovingAverageCrossStrategy(
                short_window=50, long_window=200
            )
            start_time = time.time()
            for e in events:
                cpp_strategy.calculate_signals(e)
            cpp_duration = time.time() - start_time
            print(f"C++ Implementation:    {cpp_duration:.4f} seconds")

            if cpp_duration > 0:
                speedup = py_duration / cpp_duration
                print(f"Speedup: {speedup:.2f}x")
            else:
                print("C++ duration was 0, instantaneous execution.")
        except Exception as e:
            print(f"C++ Benchmark failed: {e}")

    # C++ Fast Path Benchmark
    if CppMovingAverageCrossStrategy is not None:
        try:
            cpp_strategy_fast = CppMovingAverageCrossStrategy(
                short_window=50, long_window=200
            )
            start_time = time.time()
            for e in events:
                # Pass only price (simple float)
                cpp_strategy_fast.calculate_signal_fast(e.price)
            cpp_fast_duration = time.time() - start_time
            print(f"C++ Fast Path:         {cpp_fast_duration:.4f} seconds")

            if cpp_fast_duration > 0:
                speedup_fast = py_duration / cpp_fast_duration
                print(f"Speedup (Fast, 100k iters): {speedup_fast:.2f}x")

        except Exception as e:
            print(f"C++ Fast Path failed: {e}")


if __name__ == "__main__":
    benchmark()
