"""FastAPI application for JobRadar Web UI — routing only, no business logic."""

import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent
TMP_DIR  = Path("output/.tmp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Clean up stale temp files from any previous session on startup."""
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="JobRadar", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the dashboard page."""
    return templates.TemplateResponse(request, "index.html")
