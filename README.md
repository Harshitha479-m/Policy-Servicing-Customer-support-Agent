# Policy Servicing & Customer Support AI Agent

A read-only, retrieval-augmented insurance servicing agent that cross-references policy administration records, attached endorsements, and policyholder/broker inquiries to answer coverage questions instantly with strict citations and refusal guardrails.

---

## 📋 Requirements & Architecture Mapping

| Requirement | Implementation Details |
| :--- | :--- |
| **1. Read access to policy administration data** | SQLite repository in `app/db.py` executing parameterized `SELECT` queries across insured customers, policy schedules, terms, deductibles, premiums, and active endorsement riders. |
| **2. RAG pipeline over policy documents/endorsements** | `app/ingestion.py` extracts text from PDF, DOCX, TXT, and MD files with sliding window chunking and metadata preservation. `app/vector_store.py` builds an offline, deterministic vector index for similarity retrieval in `app/retrieval.py`. |
| **3. Conversational interface for policyholders and brokers** | Streamlit application (`streamlit_app.py`) providing role-aware perspectives, case queue selector, policyholder vs broker views, verified source citations, and interactive RAG inspection sandbox. |
| **4. Low-risk read-only scope for first deployment** | Strict architectural isolation: database queries are read-only; transactional intent classifier in `app/agent.py` intercepts and refuses mutations (cancellations, claims approvals, address updates, binding) and routes to licensed specialists; ungrounded questions below similarity thresholds trigger explicit refusals. |

---

## 🛡️ Safety & Guardrail Boundaries

1. **Read-Only Scope Enforcement**: The application exposes **zero** write/update endpoints to the agent. It cannot alter policy records, cancel coverage, or disburse claims.
2. **Transactional Request Interception**: Inquiries requesting policy cancellations, limits changes, claims filing, or credit card billing trigger a dedicated read-only refusal notice instructing users to contact authorized underwriting or claims personnel.
3. **Refusal Guardrail for Missing Evidence**: If document retrieval score is below the configured threshold (`MIN_RETRIEVAL_SCORE=0.08`), the agent refuses to guess and recommends specialist escalation.
4. **Attribution & Citations**: Every grounded answer links directly to verified policy document sources and page numbers.

---

## 🚀 Quick Start

### 1. Run with Virtual Environment
```powershell
# Activate existing virtual environment
.\.venv\Scripts\Activate.ps1

# (Optional) Re-seed demo database and re-index sample documents
python scripts/init_demo.py
python scripts/ingest_documents.py

# Launch the Streamlit application
streamlit run streamlit_app.py
```

### 2. Sign In
Use demo credentials:
- **Username**: `demo.user`
- **Password**: `change-me`

---

## 🖥️ Workspace Views

- **Overview**: Executive dashboard displaying system metrics (active policies, endorsements, indexed chunks), safety boundaries, and one-click scenario launchers.
- **Conversations**: Dual-role support workspace with conversation queue, chat stream with verified citations, policyholder details, and active endorsements drawer.
- **Policies**: Searchable policy directory with customer role indicators, terms, deductibles, premiums, risk locations, and instant "Open in Servicing Chat" buttons.
- **Knowledge Base**: Document corpus inspector and interactive RAG similarity search sandbox to test retrieval against raw chunks.

---

## 🧪 Automated Testing

Run the test suite using pytest:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Tests cover:
- Database schema and read-only repository queries (`test_db.py`)
- Authentication, PBKDF2 hashing, and session expiry (`test_auth.py`)
- Document ingestion, chunking overlap, and metadata tracking (`test_ingestion.py`)
- RAG grounding, multi-endorsement cross-referencing, role awareness, mutation guardrails, and refusal behavior (`test_rag.py`)

---

## 📂 Project Structure

```
Customer Support Agent/
├── app/
│   ├── agent.py            # Grounded policy agent with refusal & mutation guardrails
│   ├── auth.py             # Session authentication and PBKDF2 password hashing
│   ├── config.py           # Environment configuration and path resolution
│   ├── db.py               # SQLite schema, seed data, and read-only queries
│   ├── ingestion.py        # PDF/DOCX/TXT/MD extraction & metadata chunking
│   ├── logging_config.py   # Application audit logging
│   ├── retrieval.py        # Similarity retrieval and context formatting
│   └── vector_store.py     # Local deterministic vector embedding store
├── sample_documents/       # Approved policy wordings and endorsement schedules
├── scripts/
│   ├── init_demo.py        # Database initialization script
│   └── ingest_documents.py # Document ingestion and vector index build script
├── tests/                  # Unit and integration test suite
├── streamlit_app.py        # Multi-view Streamlit servicing dashboard
├── requirements.txt        # Python package dependencies
└── README.md               # Documentation and usage guide
```
