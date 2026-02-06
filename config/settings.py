"""Application settings and configuration management."""

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # API Keys
    SOCRATA_APP_TOKEN: str = os.getenv("SOCRATA_APP_TOKEN", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Socrata/OSPI Data Portal
    SOCRATA_DOMAIN: str = "data.wa.gov"

    # Cache settings
    CACHE_TTL_SECONDS: int = 86400  # 24 hours

    # App settings
    MAX_COMPARISON_ENTITIES: int = 5
    DEFAULT_YEAR: str = "2023-24"

    # LLM settings (Gemini)
    LLM_MODEL: str = "gemini-3-flash-preview"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.3

    @property
    def has_socrata_token(self) -> bool:
        return bool(self.SOCRATA_APP_TOKEN)

    @property
    def has_google_key(self) -> bool:
        return bool(self.GOOGLE_API_KEY)

    @property
    def has_anthropic_key(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Dataset IDs for data.wa.gov
# These are loaded from config/datasets.yaml but kept here as fallback
DATASET_IDS = {
    "assessment": "x73g-mrqp",  # SBA/WCAS Assessment Results (through 2023-24)
    "assessment_2024_25": "h5d9-vgwi",  # SBA/WCAS Assessment Results (2024-25+)
    "enrollment": "2rwv-gs2e",  # Enrollment by demographics
    "graduation": "76iv-8ed4",  # Graduation rates (through 2023-24)
    "graduation_2024_25": "isxb-523t",  # Graduation rates (2024-25+)
    "teachers": "yp28-ks6d",  # Teacher data
    "directory": "fhxx-d5zv",  # School directory
}
