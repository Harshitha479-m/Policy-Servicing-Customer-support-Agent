import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db import seed_demo_data
from app.logging_config import configure_logging


if __name__ == "__main__":
    configure_logging()
    seed_demo_data(settings.database_path())
    print(f"Initialized demo database at {settings.database_path()}")
