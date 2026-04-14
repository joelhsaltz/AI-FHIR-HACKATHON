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


DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4.1-mini",
}


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_api_key: str
    llm_model: str
    fhir_base: str
    fhir_username: str
    fhir_password: str


def load_settings(env_path: Path | None = None) -> Settings:
    """Load runtime settings from the workspace .env file and environment."""
    load_dotenv(env_path=env_path)

    provider = os.environ.get("LLM_PROVIDER", "").lower()
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "")

    # Backward compat: fall back to ANTHROPIC_API_KEY / ANTHROPIC_MODEL
    if not provider:
        if os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
        else:
            provider = "anthropic"
    if not api_key:
        if provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        elif provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY", "")
    if not model:
        model = os.environ.get("ANTHROPIC_MODEL", "") if provider == "anthropic" else ""
    if not model:
        model = DEFAULT_MODELS.get(provider, "")

    return Settings(
        llm_provider=provider,
        llm_api_key=api_key,
        llm_model=model,
        fhir_base=os.environ.get(
            "FHIR_BASE",
            "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4",
        ),
        fhir_username=os.environ.get("FHIR_USERNAME", "fhiruser"),
        fhir_password=os.environ.get("FHIR_PASSWORD", ""),
    )
