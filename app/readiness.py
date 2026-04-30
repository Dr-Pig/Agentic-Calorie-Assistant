import os
import sys

from .logger import logger

PROVIDER_TOKEN_ENV_VARS = {
    "builderspace": ("AI_BUILDER_TOKEN",),
    "deepseek": ("DEEPSEEK_API_KEY",),
}

PLACEHOLDER_VALUES = {"replace-me", "", "null"}


def validate_config() -> None:
    """Check required configuration on startup to fail fast."""
    missing = []
    placeholders = []

    provider_name = os.getenv("AI_MANAGER_PROVIDER", os.getenv("AI_PROVIDER", "deepseek")).strip().lower()
    required_vars = PROVIDER_TOKEN_ENV_VARS.get(provider_name, ("AI_BUILDER_TOKEN",))

    for var in required_vars:
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
