from pydantic_settings import BaseSettings, SettingsConfigDict
from app.paths import app_paths

config_file_path = app_paths.config_dir / "config.env"
env_file_target = str(config_file_path) if config_file_path.exists() else ".env"



class Settings(BaseSettings):
    app_env: str = "development"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    database_url: str = "postgresql+psycopg://socialscope:socialscope@127.0.0.1:5433/socialscope"

    # Collector & Browser settings
    instagram_max_posts: int = 10
    x_max_posts: int = 10
    facebook_max_posts: int = 10
    browser_headless: bool = True
    browser_timeout: int = 30000

    # Scheduler settings
    scheduler_enabled: bool = True
    scheduler_tick_minutes: int = 5
    max_collection_retries: int = 2
    retry_backoff_seconds: int = 5

    # AI Insights settings (Optional external LLM API)
    ai_provider: str = "mock"
    ai_api_key: str = ""
    ai_model_name: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=env_file_target,
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

