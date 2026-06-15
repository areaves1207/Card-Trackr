from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://cardtrackr:localdev@localhost:5432/cardtrackr"
    secret_key: str = "change_me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    pokemon_tcg_api_key: str = ""

    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "cardtrackr-uploads"
    r2_public_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
