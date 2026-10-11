import pytest
import pymysql
from src.core.config import settings

def is_mysql_connected():
    try:
        conn = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DB,
            connect_timeout=2
        )
        conn.close()
        return True
    except Exception:
        return False

MYSQL_AVAILABLE = is_mysql_connected()

requires_mysql = pytest.mark.skipif(
    not MYSQL_AVAILABLE,
    reason=f"MySQL server not reachable at {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}. Configure credentials in .env and start MySQL."
)

