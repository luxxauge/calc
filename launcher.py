from __future__ import annotations
import threading
import webbrowser
import uvicorn
from elektrocalc.settings import DEFAULT_HOST, DEFAULT_PORT
from elektrocalc.web.app import app


def open_browser():
    webbrowser.open(f"http://{DEFAULT_HOST}:{DEFAULT_PORT}")


def main():
    if DEFAULT_HOST in {"127.0.0.1", "localhost"}:
        threading.Timer(0.8, open_browser).start()
    uvicorn.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT, log_level="info")

if __name__ == "__main__":
    main()
