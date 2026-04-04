"""
Server entry point for OpenEnv multi-mode deployment.
This file imports the FastAPI app from the root main.py module.
"""
import sys
from pathlib import Path

# Add parent directory to path to import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

__all__ = ["app"]


def main():
    """
    Main entry point for running the server.
    Called by OpenEnv multi-mode deployment.
    """
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
