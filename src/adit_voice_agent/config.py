"""Environment configuration; values are never returned by readiness endpoints."""

from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_base_url: str = "http://127.0.0.1:8000"
    database_url: str = "sqlite:///./.cache/local.db"
    session_secret: SecretStr = SecretStr("")
    admin_username: str = "operator"
    admin_password_hash: SecretStr = SecretStr("")
    cookie_secure: bool = False
    allowed_hosts: str = "127.0.0.1,localhost"
    live_calls_enabled: bool = False
    free_trial_verified: bool = False
    allowed_phone_numbers: str = ""
    max_call_attempts: int = Field(default=10, ge=1, le=10)
    max_call_seconds: int = Field(default=180, ge=15, le=180)
    livekit_url: str = ""
    livekit_api_key: SecretStr = SecretStr("")
    livekit_api_secret: SecretStr = SecretStr("")
    livekit_agent_name: str = "adit-healthcare"
    livekit_sip_trunk_id: str = ""
    livekit_destination_country: str = ""
    google_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.6-flash"
    gemini_analysis_model: str = ""
    stt_model: str = "deepgram/nova-3"
    tts_model: str = "cartesia/sonic-3"
    tts_voice: str = ""
    supabase_url: str = ""
    supabase_service_role_key: SecretStr = SecretStr("")
    recording_bucket: str = "call-recordings"
    s3_endpoint: str = ""
    s3_region: str = ""
    s3_access_key: SecretStr = SecretStr("")
    s3_secret_key: SecretStr = SecretStr("")
    opik_api_key: SecretStr = SecretStr("")
    opik_workspace: str = ""
    opik_project_name: str = "adit-healthcare"
    opik_url_override: str = "https://www.comet.com/opik/api"
    opik_web_url: str = "https://www.comet.com/opik"
    opik_rule_id: str = ""

    @model_validator(mode="after")
    def production_security(self):
        if self.app_env == "production":
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL.")
            if not self.cookie_secure or not self.app_base_url.startswith("https://"):
                raise ValueError("Production requires HTTPS and secure cookies.")
            if "*" in self.allowed_hosts:
                raise ValueError("Production requires explicit allowed hosts.")
        return self

    @property
    def analysis_model(self) -> str:
        return self.gemini_analysis_model or self.gemini_model

    @property
    def destinations(self) -> set[str]:
        return {v.strip() for v in self.allowed_phone_numbers.split(",") if v.strip()}

    def present(self, field: str) -> bool:
        value = getattr(self, field)
        return bool(value.get_secret_value() if isinstance(value, SecretStr) else value)

    def readiness(self) -> dict:
        groups = {
            "livekit": ["livekit_url", "livekit_api_key", "livekit_api_secret", "livekit_sip_trunk_id"],
            "models": ["google_api_key", "tts_voice"],
            "storage": ["supabase_url", "supabase_service_role_key", "s3_endpoint", "s3_region", "s3_access_key", "s3_secret_key"],
            "opik": ["opik_api_key", "opik_workspace", "opik_rule_id"],
        }
        components = {
            name: {"configured": all(self.present(f) for f in fields),
                   "missing": [f.upper() for f in fields if not self.present(f)]}
            for name, fields in groups.items()
        }
        enabled = (
            self.live_calls_enabled and self.free_trial_verified and bool(self.destinations)
            and self.database_url.startswith("postgresql")
            and all(c["configured"] for c in components.values())
        )
        return {
            "calls_enabled": enabled,
            "configuration": components,
            "trial_preflight_confirmed": self.free_trial_verified,
            "live_test_verified": False,
            "note": "Configuration presence is not proof of connectivity or a successful telephone call.",
            "limits": {"attempts": self.max_call_attempts, "seconds": self.max_call_seconds, "concurrent": 1},
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
