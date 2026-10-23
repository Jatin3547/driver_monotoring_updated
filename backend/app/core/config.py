"""Centralized application configuration.

All environment-dependent values are read here, once, via pydantic-settings.
Nothing else in the codebase should call `os.environ` directly — import
`settings` from this module instead.
"""

from functools import lru_cache

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class _BaseSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
except ImportError:
    class _BaseSettings:  # type: ignore[no-redef]
        pass


class Settings(_BaseSettings):

    # Database
    database_url: str = "sqlite:///./fleet.db"

    # Auth
    secret_key: str = "dev-secret-key-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS — comma-separated list of allowed origins
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Simulation / AI mode switches. "simulation" never requires extra
    # hardware or heavy dependencies; "live" does (see README).
    gps_mode: str = "demo"
    ai_mode: str = "demo"
    ai_camera_index: int | str = 0
    ai_event_cooldown_seconds: int = 30  # min gap between incidents of the same type for the same driver

    # Computer Vision Thresholds and Durations
    ai_ear_threshold: float = 0.125
    ai_mar_threshold: float = 0.25
    ai_yaw_threshold_degrees: float = 25.0
    ai_drowsiness_duration_seconds: float = 1.0
    ai_eye_closure_warning_seconds: float = 0.6
    ai_yawn_duration_seconds: float = 1.0
    ai_distraction_duration_seconds: float = 2.0
    ai_absence_grace_seconds: float = 2.5
    ai_target_fps: int = 15
    ai_camera_reconnect_max_retries: int = 5

    # Phone Detection Settings (Pretrained YOLOv8)
    ai_phone_detection_enabled: bool = True
    ai_phone_model: str = "yolov8n.pt"
    ai_phone_confidence_threshold: float = 0.35
    ai_phone_usage_duration_seconds: float = 1.5
    ai_phone_warning_duration_seconds: float = 0.6

    environment: str = "development"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
