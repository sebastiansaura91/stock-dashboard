"""Desktop launcher for Stock Dashboard.

Starts the Streamlit server as a background process, waits for it to be
ready, then opens the app in a native PyWebView window.  When the window
is closed the Streamlit process is automatically terminated.

Usage:
    python launcher.py
"""

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import webview

_PORT = 8501
_URL = f"http://localhost:{_PORT}"
_TITLE = "Stock Dashboard"
_WIDTH = 1440
_HEIGHT = 900
_HERE = os.path.dirname(os.path.abspath(__file__))


def _start_streamlit() -> subprocess.Popen:
    """Launch Streamlit as a child process in the project directory."""
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", str(_PORT),
        "--server.headless", "true",       # don't auto-open a browser tab
        "--server.runOnSave", "false",
        "--browser.gatherUsageStats", "false",
    ]
    # Suppress Streamlit's console output to keep the launcher window clean
    return subprocess.Popen(
        cmd,
        cwd=_HERE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_server(url: str, timeout: int = 60) -> bool:
    """Poll until the server returns HTTP 200 or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    return False


def main() -> None:
    print("Starting Stock Dashboard …")
    proc = _start_streamlit()

    try:
        print(f"Waiting for server on {_URL} …")
        if not _wait_for_server(_URL):
            print("ERROR: Streamlit did not start within 60 seconds.")
            proc.terminate()
            sys.exit(1)

        print("Server ready — opening window.")
        webview.create_window(
            _TITLE,
            _URL,
            width=_WIDTH,
            height=_HEIGHT,
            min_size=(900, 600),
        )
        webview.start()          # blocks until the window is closed

    finally:
        print("Shutting down server …")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Done.")


if __name__ == "__main__":
    main()
