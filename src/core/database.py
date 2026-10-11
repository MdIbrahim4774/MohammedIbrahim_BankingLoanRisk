import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from src.core.config import settings

logger = logging.getLogger("banking_loan.database")

# Ensure data directory exists for any file assets
os.makedirs("data", exist_ok=True)

ACTIVE_DATABASE_URL = settings.get_database_url

def create_db_engine():
    """
    Creates and returns pure MySQL SQLAlchemy engine using pymysql.
    """
    db_url = settings.get_database_url
    logger.info(f"Connecting to MySQL: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB} (user: {settings.MYSQL_USER})")
    
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20
    )
    return engine

engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes database tables directly in MySQL.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"MySQL tables verified/initialized successfully in `{settings.MYSQL_DB}`.")
    except Exception as e:
        logger.error(
            f"Failed to initialize MySQL tables on {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}. "
            f"Please verify MySQL server is running and .env credentials are correct. Error: {e}"
        )
        raise
