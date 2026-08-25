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

    # Assessment subgroup/grade options
    # Same caveat as GRADE_LEVELS: these are the literal `studentgroup` values the
    # datasets store, including their irregular spacing. The tidier spellings live
    # in STUDENT_GROUP_LABELS and are for display only.
    STUDENT_GROUPS_CORE: list = [
        "All Students", "Low-Income", "English Language Learners",
        "Students with Disabilities", "White", "Hispanic/ Latino of any race(s)",
        "Black/ African American", "Asian",
    ]
    STUDENT_GROUPS_EXTENDED: list = [
        "American Indian/ Alaskan Native", "Native Hawaiian/Pacific Islander",
        "Two Or More Races", "Female", "Male", "Migrant", "Section 504",
        "Homeless", "Military Parent", "Foster Care",
    ]

    STUDENT_GROUP_LABELS: dict = {
        "Hispanic/ Latino of any race(s)": "Hispanic/Latino of any race(s)",
        "Black/ African American": "Black/African American",
        "American Indian/ Alaskan Native": "American Indian/Alaskan Native",
        "Two Or More Races": "Two or More Races",
    }

    # Two group names were respelled between dataset years. Maps the canonical
    # (current) value to the last school year that used the older spelling and
    # what that spelling was.
    STUDENT_GROUP_YEAR_ALIASES: dict = {
        "Two Or More Races": ("2022-23", "TwoorMoreRaces"),
        "Native Hawaiian/Pacific Islander": ("2023-24", "Native Hawaiian/ Other Pacific Islander"),
    }
    # NOTE: these are the literal values the OSPI assessment datasets store in
    # the `gradelevel` column. They are zero-padded codes, not display labels —
    # querying with "3rd Grade" matches zero rows. Use GRADE_LABELS for display.
    GRADE_LEVELS: list = [
        "All Grades", "03", "04", "05", "06", "07", "08", "10", "11",
    ]

    GRADE_LABELS: dict = {
        "All Grades": "All Grades",
        "03": "3rd Grade",
        "04": "4th Grade",
        "05": "5th Grade",
        "06": "6th Grade",
        "07": "7th Grade",
        "08": "8th Grade",
        "10": "10th Grade",
        "11": "11th Grade",
    }

    # LLM settings (Gemini)
    LLM_MODEL: str = "gemini-3-flash-preview"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.3

    def student_group_label(self, group: str) -> str:
        """Display label for an API student group value."""
        return self.STUDENT_GROUP_LABELS.get(group, group)

    def student_group_for_year(self, group: str, school_year: str) -> str:
        """Resolve a student group to the spelling used by that year's dataset."""
        alias = self.STUDENT_GROUP_YEAR_ALIASES.get(group)
        if alias and school_year <= alias[0]:
            return alias[1]
        return group

    def grade_label(self, grade_code: str) -> str:
        """Display label for an API grade code (e.g. "03" -> "3rd Grade")."""
        return self.GRADE_LABELS.get(grade_code, grade_code)

    def grade_code(self, grade: str) -> str:
        """Normalize a display label back to the API grade code; passes codes through."""
        if grade in self.GRADE_LABELS:
            return grade
        for code, label in self.GRADE_LABELS.items():
            if label == grade:
                return code
        return grade

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
}
