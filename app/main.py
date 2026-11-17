from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, patients
from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import (
    AIServiceException,
    DatabaseOperationException,
    PatientNotFoundException,
    ValidationException,
    VitalSenseBaseException,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("vitalsense")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: initializes database schema on startup."""
    logger.info("Initializing VitalSense database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("VitalSense AI backend initialized successfully.")
    yield
    logger.info("VitalSense AI backend shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Patient Health Insights & Blood Test Management System",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(health.router, prefix="/api")
app.include_router(patients.router, prefix="/api")


# Domain Exception Handlers
@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": exc.message,
            "errors": exc.errors
        }
    )


@app.exception_handler(PatientNotFoundException)
async def patient_not_found_handler(request: Request, exc: PatientNotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "success": False,
            "message": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(AIServiceException)
async def ai_service_exception_handler(request: Request, exc: AIServiceException):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.is_transient else status.HTTP_502_BAD_GATEWAY,
        content={
            "success": False,
            "message": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(VitalSenseBaseException)
async def vitalsense_base_handler(request: Request, exc: VitalSenseBaseException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Never expose internal database stack traces or sensitive environment variables
    logger.error("Unhandled server exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An internal server error occurred. Please contact the system administrator."
        }
    )


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "documentation": "/docs",
        "health_check": "/api/health",
        "version": settings.APP_VERSION
    }
