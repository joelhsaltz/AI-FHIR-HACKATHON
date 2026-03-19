"""Environment loading and runtime settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


def load_dotenv(env_path: Path | None = None, override: bool = True) -> dict[str, str]:
    """Load key=value pairs from a local .env file."""
    path = env_path or DEFAULT_ENV_PATH
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        loaded[key] = value
        if override or key not in os.environ:
            os.environ[key] = value
    return loaded


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    anthropic_model: str
    fhir_base: str
    fhir_username: str
    fhir_password: str


def load_settings(env_path: Path | None = None) -> Settings:
    """Load runtime settings from the workspace .env file and environment."""
    load_dotenv(env_path=env_path)
    return Settings(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        fhir_base=os.environ.get(
            "FHIR_BASE",
            "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4",
        ),
        fhir_username=os.environ.get("FHIR_USERNAME", "fhiruser"),
        fhir_password=os.environ.get("FHIR_PASSWORD", ""),
    )
