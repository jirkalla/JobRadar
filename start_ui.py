"""Start the JobRadar web UI. Loads .env then launches uvicorn."""
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import uvicorn  # noqa: E402 — must import after env is loaded

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8471
    uvicorn.run("ui.main_ui:app", reload=True, port=port)
