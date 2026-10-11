import os
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Banking Loan Risk Analysis Application"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Pure MySQL Database Configuration
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "loan_risk_db"
    
    # Optional full DATABASE_URL override in .env
    DATABASE_URL: Optional[str] = None
    
    # JWT & Auth
    SECRET_KEY: str = "bank-credit-risk-super-secret-key-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Data Pipeline Directories
    RAW_DATA_DIR: str = "data/raw"
    PROCESSED_DATA_DIR: str = "data/processed"
    
    # Risk Engine Thresholds (Configurable)
    HIGH_RISK_MAX_DELAY_MONTHS: int = 2
    HIGH_RISK_UTILIZATION_THRESHOLD: float = 0.85
    HIGH_RISK_REPAYMENT_RATIO_THRESHOLD: float = 0.20
    
    MED_RISK_UTILIZATION_THRESHOLD: float = 0.60
    MED_RISK_REPAYMENT_RATIO_THRESHOLD: float = 0.50
    
    REVIEW_CREDIT_LIMIT_THRESHOLD: float = 500000.0
    REVIEW_UTILIZATION_THRESHOLD: float = 0.90
    REVIEW_CONSECUTIVE_DELAYS: int = 2

    @property
    def get_database_url(self) -> str:
        if self.DATABASE_URL and self.DATABASE_URL.strip():
            return self.DATABASE_URL.strip()
        encoded_pass = f":{quote_plus(self.MYSQL_PASSWORD)}" if self.MYSQL_PASSWORD else ""
        return f"mysql+pymysql://{self.MYSQL_USER}{encoded_pass}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()
