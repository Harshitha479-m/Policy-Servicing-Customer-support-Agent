from app.agent import GroundedPolicyAgent, REFUSAL
from app.db import seed_demo_data
from app.ingestion import chunk_text, ingest_directory
from app.vector_store import LocalVectorStore


def make_agent(tmp_path):
    database = tmp_path / "policy.db"
    seed_demo_data(database)
    chunks = ingest_directory(__import__('pathlib').Path(__file__).parents[1] / "sample_documents")
    store = LocalVectorStore.build(chunks)
    return GroundedPolicyAgent(store, database, top_k=3, min_score=0.01)


def test_chunking_has_overlap_and_metadata():
    chunks = chunk_text("alpha " * 400, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert chunks[0][-20:] == chunks[1][:20]


def test_grounded_answer_contains_sources(tmp_path):
    response = make_agent(tmp_path).answer("Is a burst pipe covered and what deductible applies?", "POL-4821-AX")
    assert response.grounded
    assert "$1,000" in response.answer
    assert response.citations
    assert all(citation.source.startswith("DEMO_") for citation in response.citations)


def test_unanswerable_question_refuses(tmp_path):
    response = make_agent(tmp_path).answer("What is the nearest airport?", "POL-4821-AX")
    assert not response.grounded
    assert response.answer == REFUSAL
    assert response.citations == []


def test_unknown_policy_is_not_guessed(tmp_path):
    response = make_agent(tmp_path).answer("Is water damage covered?", "POL-NOT-FOUND")
    assert not response.grounded
    assert "could not find" in response.answer


def test_commercial_auto_newly_acquired_vehicle(tmp_path):
    response = make_agent(tmp_path).answer("Can I add my new electric vehicle before the weekend?", "POL-7710-QZ")
    assert response.grounded
    assert "14 days" in response.answer
    assert response.citations
    assert any("commercial_auto" in c.source.lower() for c in response.citations)


def test_certificate_of_insurance_request(tmp_path):
    response = make_agent(tmp_path).answer("I need an updated certificate of insurance.", "POL-1193-KM")
    assert response.grounded
    assert "Certificate" in response.answer or "certificate" in response.answer
    assert response.citations
    assert any("commercial_property" in c.source.lower() for c in response.citations)


def test_mutation_request_refusal(tmp_path):
    response = make_agent(tmp_path).answer("Please cancel my policy immediately and refund my premium.", "POL-4821-AX")
    assert not response.grounded
    assert response.is_mutation_refusal
    assert "read-only" in response.answer.lower()
    assert response.citations == []

