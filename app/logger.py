import logging
import os
import sys

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger

logger = setup_logger("canary")
