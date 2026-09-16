from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "demo")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/policy_support.db")
    vector_store_path: Path = ROOT_DIR / os.getenv("VECTOR_STORE_PATH", "data/vector_store.pkl")
    documents_dir: Path = ROOT_DIR / os.getenv("DOCUMENTS_DIR", "sample_documents")
    top_k: int = int(os.getenv("TOP_K", "5"))
    min_retrieval_score: float = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.08"))
    session_ttl_minutes: int = int(os.getenv("SESSION_TTL_MINUTES", "60"))
    demo_username: str = os.getenv("DEMO_USERNAME", "demo.user")
    demo_password: str = os.getenv("DEMO_PASSWORD", "change-me")

    def database_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError("This demo supports only sqlite:/// DATABASE_URL values")
        path = Path(self.database_url[len(prefix):])
        return path if path.is_absolute() else ROOT_DIR / path


settings = Settings()
