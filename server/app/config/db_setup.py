from dataclasses import dataclass
from urllib.parse import quote_plus

@dataclass(frozen=True)
class Settings:

    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "appdbtest"
    db_user: str = "sabata"
    db_password: str = "apptest"

    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_user)
        pwd  = quote_plus(self.db_password)
        return f"postgresql://{user}:{pwd}@{self.db_host}:{self.db_port}/{self.db_name}"

settings = Settings()

