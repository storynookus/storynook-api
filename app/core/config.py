from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StoryNook API"
    api_v1_prefix: str = "/api/v1"

    app_env: str = "dev"
    dev_api_token: str = ""
    prod_api_token: str = ""
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    @property
    def active_api_token(self) -> str:
        token = self.prod_api_token if self.app_env.lower() == "prod" else self.dev_api_token
        if not token:
            env_name = "PROD_API_TOKEN" if self.app_env.lower() == "prod" else "DEV_API_TOKEN"
            raise ValueError(f"Missing required token: {env_name}")
        return token


settings = Settings()
