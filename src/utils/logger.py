import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name: str = "banking_loan") -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Console Handler
        c_handler = logging.StreamHandler()
        c_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        c_handler.setFormatter(c_format)
        logger.addHandler(c_handler)

        # File Handler (rotating)
        f_handler = RotatingFileHandler("logs/banking_loan.log", maxBytes=10*1024*1024, backupCount=5)
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
        f_handler.setFormatter(f_format)
        logger.addHandler(f_handler)

    return logger

app_logger = setup_logger()

