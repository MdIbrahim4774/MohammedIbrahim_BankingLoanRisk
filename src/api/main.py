from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.core.database import init_db
from src.utils.logger import app_logger
from src.utils.scheduler import start_scheduler, shutdown_scheduler

from src.api.routers import auth, customers, risk_analysis, analytics, etl

@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("Initializing Banking Loan Risk Analysis Application...")
    init_db()
    start_scheduler()
    yield
    app_logger.info("Shutting down application...")
    shutdown_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    ## Banking Loan Risk Analysis Application API
    A full-stack banking analysis microservice platform for customer credit data ETL, 
    risk scoring, automated rule-based risk band classification (Low, Medium, High), 
    delinquency tracking, and credit risk dashboarding.
    
    ### Key Features:
    * **ETL Pipeline**: Extracts and cleans credit records, performs record-level reconciliation and data-quality checks.
    * **Credit Risk Engine**: Multi-factor scoring, Low/Medium/High risk bands, manual review exception queue.
    * **Demographic Analytics**: KPIs across Education, Age brackets, Marital status, and Gender.
    * **Role-Based Access Control**: Separate workflows for Underwriting Analysts and Administrators.
    """,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(customers.router, prefix=settings.API_V1_PREFIX)
app.include_router(risk_analysis.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(etl.router, prefix=settings.API_V1_PREFIX)

@app.get("/", tags=["System"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_check": "/health",
        "api_prefix": settings.API_V1_PREFIX
    }

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)

