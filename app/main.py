"""FastAPI application entrypoint for Dress 2 Decor AI Automation."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.database import init_db
from app.api.routes import router as api_router

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Dress 2 Decor — AI E-commerce Automation",
    description="AI-powered order management, vendor support, and meeting scheduling demo.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the Dress 2 Decor AI Automation Dashboard."""
    return templates.TemplateResponse(request, "index.html")
