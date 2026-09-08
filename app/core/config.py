from pydantic_settings import BaseSettings


ACCESS_TOKEN_EXPIRE_HOURS = 6
REFRESH_TOKEN_EXPIRE_HOURS = 9

# Portas do dev server do frontend. Mantém o comportamento que estava fixo no
# main.py quando CORS_ORIGINS não é informado.
DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000,"
    "http://127.0.0.1:3000,"
    "http://localhost:3001,"
    "http://127.0.0.1:3001"
)


class Settings(BaseSettings):
    database_url: str

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Origens autorizadas no CORS, separadas por vírgula. String em vez de list
    # para o .env continuar legível — o pydantic exigiria JSON numa list.
    cors_origins: str = DEFAULT_CORS_ORIGINS

    # Prefixo público quando a API é servida sob um subcaminho no proxy reverso
    # (ex.: /api). Vazio = sem prefixo, que é o caso rodando direto.
    root_path: str = ""

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
