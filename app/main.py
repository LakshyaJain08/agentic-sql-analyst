"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_v1_router
from app.database.connection import check_db_health
from app.database.seed_data import seed_database
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    # Ensure database tables exist and are seeded
    try:
        seed_database(force_reseed=False)
        print("[Startup] Database connection verified and seeded.")
    except Exception as e:
        print(f"[Startup Warning] Database seed check error: {e}")
    yield


settings = get_settings()

app = FastAPI(
    title="Agentic AI Data Analyst API",
    description="Natural Language to SQL analytics agent powered by LangGraph, PostgreSQL/SQLite, and SQLGlot.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Streamlit or custom web frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint reporting API and database connectivity status."""
    db_status = check_db_health()
    return {
        "status": "online",
        "app_env": settings.APP_ENV,
        "database": db_status
    }


# Include API Routes
app.include_router(api_v1_router, prefix="/api/v1", tags=["Data Analyst"])

# Mount Vanilla HTML/CSS/JS Frontend
import os
from fastapi.staticfiles import StaticFiles

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.API_PORT, reload=True)
