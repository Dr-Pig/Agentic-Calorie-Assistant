import os
import sys

from .logger import logger

REQUIRED_ENV_VARS = [
    "AI_BUILDER_TOKEN",
]

PLACEHOLDER_VALUES = {"replace-me", "", "null"}


def validate_config() -> None:
    """Check required configuration on startup to fail fast."""
    missing = []
    placeholders = []
    
    for var in REQUIRED_ENV_VARS:
        val = os.getenv(var, "").strip()
        if not val:
            missing.append(var)
        elif val in PLACEHOLDER_VALUES:
            placeholders.append(var)
            
    if missing or placeholders:
        logger.critical(
            f"Startup validation failed! Missing vars: {missing}. Placeholder vars: {placeholders}. "
            f"Please check your .env file."
        )
        sys.exit(1)
        
    logger.info("Startup config validation passed.")
