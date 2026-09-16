from pathlib import Path

from app.ingestion import extract_document, ingest_file


def test_text_ingestion_has_stable_metadata(tmp_path):
    source = tmp_path / "DEMO_test.txt"
    source.write_text("DEMO / SAMPLE DATA\nWater damage is covered subject to exclusions.", encoding="utf-8")
    chunks = ingest_file(source)
    assert chunks[0].source == "DEMO_test.txt"
    assert chunks[0].document_type == "txt"
    assert chunks[0].page is None
    assert chunks[0].chunk_id


def test_unsupported_document_type(tmp_path):
    source = tmp_path / "notes.csv"
    source.write_text("x,y", encoding="utf-8")
    try:
        extract_document(source)
    except ValueError as error:
        assert "Unsupported" in str(error)
    else:
        raise AssertionError("unsupported files must be rejected")
