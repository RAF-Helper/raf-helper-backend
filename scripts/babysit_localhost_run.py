import logging
from logging.handlers import RotatingFileHandler
import subprocess
import re
import threading
import time
import requests
import sys
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# ==============================
# CONFIGURATION
# ==============================

SCRIPT_PATH = "./scripts/run_elastic_mirror.sh"

APP_LOG_FILE = os.getenv("BABYSIT_SCRIPT_LOGS_PATH", "logs/localhost_run_babysitter.log")
SCRIPT_LOG_FILE = os.getenv("BABYSIT_PROCESS_LOGS_PATH", "logs/localhost_run.log")

API_ENDPOINT = f"{os.getenv('SERVICE_URL', 'http://localhost:8000')}/admin/elastic/update-url"

ADMIN_TOKEN = os.getenv("ELASTICSEARCH_UPDATE_PASSWORD")

RESTART_DELAY = 3
REQUEST_TIMEOUT = 10
RETRY_DELAY = 30

URL_REGEX = re.compile(r"https://[a-zA-Z0-9\-\.]+\.lhr\.life")

SUCCESS_MESSAGE = "Elasticsearch URL updated successfully"

# ==============================
# LOGGERS
# ==============================

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s"
)

file_handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=5_000_000, backupCount=3)
file_handler.setFormatter(formatter)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stdout_handler)

current_url = None
retry_thread = None
stop_event = threading.Event()
lock = threading.Lock()

# ==============================
# HELPERS
# ==============================

def extract_url(line: str) -> Optional[str]:
    match = URL_REGEX.search(line)
    return match.group(0) if match else None


def is_valid_response(data: dict) -> bool:
    return (
        isinstance(data, dict)
        and data.get("message") == SUCCESS_MESSAGE
        and data.get("connected") is True
    )


def retry_sender(url: str, stop_event: threading.Event):
    """Retry sending URL until success or interrupted."""
    logger.info(f"Retry loop started for: {url}")

    while not stop_event.is_set():
        try:
            response = requests.post(
                API_ENDPOINT,
                json={
                    "url": url,
                },
                headers={
                    "X-Admin-Token": ADMIN_TOKEN,
                    "Content-Type": "application/json",
                },
                timeout=REQUEST_TIMEOUT,
            )

            try:
                data = response.json()
            except ValueError:
                data = None

            if response.status_code == 200 and is_valid_response(data):
                logger.info(f"[SUCCESS] URL accepted: {url}")
                return
            else:
                logger.warning(f"Bad response: {response.status_code} | {data}")

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")

        # Wait but allow interruption
        for _ in range(RETRY_DELAY):
            if stop_event.is_set():
                logger.info(f"Retry interrupted for: {url}")
                return
            time.sleep(1)


def start_retry(url: str):
    global retry_thread, stop_event

    # Stop previous retry
    if retry_thread and retry_thread.is_alive():
        stop_event.set()
        retry_thread.join()

    # Reset stop event
    stop_event = threading.Event()

    # Start new retry thread
    retry_thread = threading.Thread(
        target=retry_sender,
        args=(url, stop_event),
        daemon=True,
    )
    retry_thread.start()

# ==============================
# CORE LOOP
# ==============================

def run_and_monitor():
    global current_url

    while True:
        logger.info("Starting shell script...")

        process = subprocess.Popen(
            ["bash", SCRIPT_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        try:
            with open(SCRIPT_LOG_FILE, "a+") as script_log:
                for line in process.stdout:
                    line = line.rstrip()

                    # write ONLY to script log file
                    script_log.write(line + "\n")
                    script_log.flush()


                    url = extract_url(line)

                    if url:
                        with lock:
                            if url != current_url:
                                logger.info(f"New URL detected: {url}")
                                current_url = url
                                start_retry(url)

        except Exception as e:
            logger.error(f"Exception: {e}")

        finally:
            process.stdout.close()
            return_code = process.wait()
            logger.warning(f"Script exited with code {return_code}")

        logger.info(f"Restarting in {RESTART_DELAY} seconds...\n")
        time.sleep(RESTART_DELAY)

# ==============================
# ENTRY
# ==============================

if __name__ == "__main__":
    try:
        run_and_monitor()
    except KeyboardInterrupt:
        logger.info("\nStopping...")
        stop_event.set()
        if retry_thread:
            retry_thread.join()
        sys.exit(0)
