from __future__ import annotations

import argparse
import os
import subprocess
import sys


def run_api(host: str = "127.0.0.1", port: int = 8000, reload: bool = True):
    """Starts the FastAPI backend using Uvicorn."""
    import uvicorn
    print(f"Starting VitalSense AI API on http://{host}:{port}...")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


def run_frontend():
    """Starts the Streamlit frontend application."""
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", frontend_path, "--server.port=8501", "--server.headless=true"]
    print("Starting VitalSense AI Streamlit UI on http://localhost:8501...")
    subprocess.run(cmd)


def run_tests():
    """Runs the full Pytest test suite."""
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    print("Running VitalSense AI Test Suite...")
    res = subprocess.run(cmd)
    sys.exit(res.returncode)


def run_seed():
    """Executes the exact 10 test cases from Section 9 & 10."""
    from scripts.seed_data import run_seed_import
    run_seed_import()


def main():
    parser = argparse.ArgumentParser(description="VitalSense AI Application Launcher")
    parser.add_argument(
        "mode",
        choices=["api", "frontend", "test", "seed", "all"],
        nargs="?",
        default="frontend",
        help="Target component to launch (default: frontend)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="API Host")
    parser.add_argument("--port", type=int, default=8000, help="API Port")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload for API")

    args = parser.parse_args()

    if args.mode == "api":
        run_api(host=args.host, port=args.port, reload=not args.no_reload)
    elif args.mode == "frontend":
        run_frontend()
    elif args.mode == "test":
        run_tests()
    elif args.mode == "seed":
        run_seed()
    elif args.mode == "all":
        import threading
        t = threading.Thread(target=run_api, kwargs={"host": args.host, "port": args.port, "reload": False})
        t.daemon = True
        t.start()
        run_frontend()


if __name__ == "__main__":
    main()
