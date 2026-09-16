import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.ingestion import ingest_directory
from app.logging_config import configure_logging
from app.vector_store import LocalVectorStore


if __name__ == "__main__":
    configure_logging()
    chunks = ingest_directory(settings.documents_dir)
    store = LocalVectorStore.build(chunks)
    store.save(settings.vector_store_path)
    print(f"Indexed {len(chunks)} chunks from {settings.documents_dir}")
