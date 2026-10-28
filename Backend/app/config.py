import os
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator


class Settings(BaseModel):
    database_url: str
    redis_url: str = 'redis://localhost:6379/0'
    redis_prefix: str = 'frame:auth:'
    access_token_secret: str = Field(min_length=32)
    refresh_token_secret: str = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=14, gt=0)
    reset_code_ttl_seconds: int = Field(default=300, gt=0)
    reset_token_ttl_seconds: int = Field(default=600, gt=0)
    reset_request_cooldown_seconds: int = Field(default=60, gt=0)
    reset_code_max_attempts: int = Field(default=5, gt=0)
    cookie_secure: bool = False
    cookie_samesite: str = 'lax'
    app_env: str = 'local'
    allowed_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'

    @model_validator(mode='after')
    def validate_security(self):
        if self.cookie_samesite not in {'lax', 'strict', 'none'}:
            raise ValueError('Invalid COOKIE_SAMESITE')
        if self.access_token_secret == self.refresh_token_secret:
            raise ValueError('Token secrets must differ')
        if self.app_env != 'local':
            self.cookie_secure = True
        if self.cookie_samesite == 'none' and not self.cookie_secure:
            raise ValueError('SameSite=None requires Secure')
        return self


@lru_cache
def get_settings():
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    return Settings(**{name: os.environ[name.upper()] for name in Settings.model_fields if name.upper() in os.environ})
