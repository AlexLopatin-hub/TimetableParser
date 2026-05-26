from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    tg_bot_api: SecretStr = Field(default=..., validation_alias="TG_BOT_API")
    uni_base_url: HttpUrl = Field(default=..., validation_alias="UNI_BASE_URL")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
