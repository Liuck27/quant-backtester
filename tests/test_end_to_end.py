import time
import requests
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/integration_test.log"),
    ],
)
logger = logging.getLogger("IntegrationTest")

BASE_URL = "http://localhost:8000"


def wait_for_api(timeout=60):
    """Wait for API to become healthy."""
    logger.info("Waiting for API to be healthy...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                if data["status"] == "healthy" and data["database"] == "connected":
                    logger.info("API is healthy and connected to DB!")
                    return True
                else:
                    logger.warning(f"API unhealthy: {data}")
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            if "data" in locals():
                logger.error(f"Response data: {data}")

        time.sleep(1)
        print(".", end="", flush=True)

    logger.error("Timeout waiting for API health.")
    return False


def run_integration_test():
    """Run full end-to-end test scenario."""

    # 1. Start Backtest
    logger.info("1. Submitting backtest job...")
    payload = {
        "symbol": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-06-01",
        "strategy": "ma_crossover",
        "parameters": {"short_window": 10, "long_window": 50},
        "initial_capital": 100000.0,
    }

    resp = requests.post(f"{BASE_URL}/backtest/run", json=payload)
    if resp.status_code != 200:
        logger.error(f"Failed to submit job: {resp.text}")
        return False

    job_id = resp.json()["job_id"]
    logger.info(f"Job submitted. ID: {job_id}")

    # 2. Poll for Completion
    logger.info("2. Polling for job completion...")
    for _ in range(30):  # 30 seconds timeout
        resp = requests.get(f"{BASE_URL}/backtest/{job_id}")
        data = resp.json()
        status = data["status"]

        if status == "completed":
            logger.info("Job completed successfully!")
            break
        elif status == "failed":
            logger.error(f"Job failed: {data.get('error')}")
            return False

        time.sleep(1)
    else:
        logger.error("Timeout waiting for job completion.")
        return False

    # 3. Verify DB Integrity
    logger.info("3. Verifying persistence in Database...")
    resp = requests.get(f"{BASE_URL}/db/results/{job_id}")

    if resp.status_code != 200:
        logger.error(f"Failed to retrieve DB results: {resp.text}")
        return False

    db_data = resp.json()

    # Assertions
    assert db_data["job_id"] == job_id
    assert db_data["status"] == "completed"
    assert db_data["trade_count"] > 0
    assert db_data["metrics"]["total_return"] != 0.0

    logger.info("[SUCCESS] Database Verification Passed!")
    logger.info(f"   Trades Stored: {db_data['trade_count']}")
    logger.info(f"   Total Return:  {db_data['metrics']['total_return']:.2f}%")

    return True


if __name__ == "__main__":
    if not wait_for_api():
        sys.exit(1)

    if run_integration_test():
        logger.info("\n[SUCCESS] ALL TESTS PASSED! System is ready for production.")
        sys.exit(0)
    else:
        logger.error("\n[FAILURE] TESTS FAILED.")
        sys.exit(1)
