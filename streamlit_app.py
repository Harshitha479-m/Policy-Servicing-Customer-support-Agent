from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from app.agent import GroundedPolicyAgent
from app.auth import authenticate, session_is_valid
from app.config import settings
from app.db import (
    find_policy,
    list_all_endorsements,
    list_endorsements,
    list_policies,
    search_policies,
    seed_demo_data,
)
from app.ingestion import ingest_directory
from app.logging_config import configure_logging
from app.retrieval import retrieve
from app.vector_store import LocalVectorStore

configure_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Policy Servicing & Customer Support Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Manrope:wght@600;700;800&display=swap');
    :root {
        --ink: #1f2a27;
        --muted: #6b7771;
        --teal: #0d655b;
        --teal-light: #e6f3f0;
        --cream: #f6f3ed;
        --paper: #ffffff;
        --line: #e3dfd6;
        --accent: #235347;
    }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
    .stApp { background: var(--cream); }
    .block-container { max-width: 1520px; padding: 2rem 2.8rem 3rem; }
    h1, h2, h3, h4 { font-family: 'Manrope', sans-serif; letter-spacing: -0.03em; }
    h1 { font-size: 1.95rem !important; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 0.98rem !important; }
    
    [data-testid="stSidebar"] { background: #ebe6dc; border-right: 1px solid #dad4c6; }
    [data-testid="stSidebar"] .block-container { padding: 1.8rem 1.1rem; }
    
    .brand { font: 800 1.15rem 'Manrope', sans-serif; margin-bottom: 2rem; display: flex; align-items: center; }
    .brand-mark { display: inline-grid; place-items: center; width: 30px; height: 30px; border-radius: 8px; background: var(--teal); color: #fff; margin-right: 10px; font-weight: 800; }
    
    .eyebrow { color: #818d86; letter-spacing: 0.12em; font-size: 0.68rem; font-weight: 700; text-transform: uppercase; }
    .subtle { color: var(--muted); font-size: 0.82rem; }
    
    .card { background: var(--paper); border: 1px solid var(--line); border-radius: 9px; padding: 1.1rem; margin-bottom: 0.9rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
    .card-highlight { background: #fdfcf9; border-left: 4px solid var(--teal); }
    
    .metric-card { min-height: 95px; background: var(--paper); border: 1px solid var(--line); border-radius: 9px; padding: 1rem; }
    .metric-name { color: var(--muted); font-size: 0.73rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-value { font: 800 1.7rem 'Manrope', sans-serif; margin: 0.25rem 0; color: var(--ink); }
    .metric-note { color: var(--teal); font-size: 0.72rem; font-weight: 500; }
    
    .readonly-banner { background: #e3f0ea; border: 1px solid #c9e2d5; border-radius: 8px; padding: 0.75rem 0.9rem; color: #216149; font-size: 0.78rem; line-height: 1.4; }
    
    .case { border: 1px solid var(--line); background: var(--paper); border-radius: 8px; padding: 0.8rem; margin: 0.45rem 0; transition: all 0.15s ease; }
    .case:hover { border-color: var(--teal); box-shadow: 0 2px 5px rgba(0,0,0,0.04); }
    .case-name { font-weight: 700; font-size: 0.86rem; }
    .case-topic { color: var(--muted); font-size: 0.73rem; margin-top: 2px; }
    .case-meta { float: right; color: var(--muted); font-size: 0.7rem; }
    
    .badge { padding: 0.18rem 0.5rem; border-radius: 999px; font-size: 0.64rem; font-weight: 700; display: inline-block; }
    .open { background: #e2f2e9; color: #1e7054; }
    .waiting { background: #fef1d6; color: #8d5c0e; }
    .resolved { background: #eaedea; color: #69736c; }
    .role-broker { background: #e7eefc; color: #1e4f9b; }
    .role-policyholder { background: #eef6ec; color: #286b3b; }
    
    .answer-box { background: #eaf4ef; border: 1px solid #d0e7dc; border-radius: 9px; padding: 1.1rem; line-height: 1.55; }
    .answer-label { color: #2e7a5e; letter-spacing: 0.1em; font-size: 0.65rem; font-weight: 800; margin-bottom: 0.45rem; text-transform: uppercase; }
    
    .refusal-box { background: #fcf1f1; border: 1px solid #f3d1d1; border-radius: 9px; padding: 1.1rem; line-height: 1.55; color: #8e2a2a; }
    .refusal-label { color: #b03535; letter-spacing: 0.1em; font-size: 0.65rem; font-weight: 800; margin-bottom: 0.45rem; text-transform: uppercase; }
    
    .source-pill { display: inline-block; background: #e9f0ec; border: 1px solid #d4e3db; border-radius: 6px; padding: 0.3rem 0.6rem; margin: 0.25rem 0.35rem 0.25rem 0; font-size: 0.73rem; color: #2b5042; }
    
    .doc-chunk { background: #ffffff; border: 1px solid var(--line); border-radius: 8px; padding: 0.9rem; margin-bottom: 0.65rem; }
    .doc-meta { font-size: 0.72rem; color: var(--muted); margin-bottom: 0.4rem; }
    
    .stButton>button { border-radius: 7px; font-weight: 600; }
    .stButton>button[kind="primary"] { background: var(--teal); border-color: var(--teal); color: #fff; }
    </style>
    """, unsafe_allow_html=True)


def ensure_login() -> bool:
    user = st.session_state.get("user")
    created_at = st.session_state.get("created_at")
    if user and created_at and session_is_valid(created_at, settings.session_ttl_minutes):
        return True
    st.markdown('<div class="brand"><span class="brand-mark">🛡️</span>Policy Servicing & Customer Support Agent</div>', unsafe_allow_html=True)
    st.title("Secure policy servicing workspace")
    st.caption("Read-only access to approved policy data and indexed policy documents.")
    with st.form("login"):
        username = st.text_input("Username", value=settings.demo_username)
        password = st.text_input("Password", type="password", value="change-me")
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        user = authenticate(username, password, settings.demo_username, settings.demo_password)
        if user:
            st.session_state.user = user
            st.session_state.created_at = datetime.now(timezone.utc)
            st.rerun()
        st.error("Invalid credentials.")
    st.info(f"Default demo credentials: `{settings.demo_username}` / `change-me`")
    return False


def get_or_create_store() -> LocalVectorStore:
    # Ensure database is seeded with demo records
    try:
        seed_demo_data(settings.database_path())
    except Exception as e:
        logger.warning("Database seed check: %s", e)

    # Load or dynamically build the vector store
    if settings.vector_store_path.exists():
        try:
            return LocalVectorStore.load(settings.vector_store_path)
        except Exception:
            pass

    # Build dynamically from sample_documents directory
    chunks = ingest_directory(settings.documents_dir)
    store = LocalVectorStore.build(chunks)
    try:
        store.save(settings.vector_store_path)
    except Exception:
        pass
    return store


inject_css()
if not ensure_login():
    st.stop()

store = get_or_create_store()
db_path = settings.database_path()
all_policies = list_policies(db_path)
all_endorsements = list_all_endorsements(db_path)

# ----------------- SIDEBAR NAVIGATION -----------------
with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark">🛡️</span>Policy Servicing</div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">NAVIGATION</div>', unsafe_allow_html=True)
    section = st.radio(
        "Workspace View",
        ["Overview", "Conversations", "Policies", "Knowledge base"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown(
        '<div class="readonly-banner"><b>🔒 Read-Only Deployment</b><br>'
        '<span style="font-size:0.71rem">Strictly SELECT queries. Transactions, address changes, claims, or coverage binding require underwriting referral.</span></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(f'<div class="subtle">Signed in as <b>{st.session_state.user.username}</b><br>Session active ({settings.session_ttl_minutes}m TTL)</div>', unsafe_allow_html=True)
    if st.button("Sign out", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# =======================================================
# SECTION 1: OVERVIEW
# =======================================================
if section == "Overview":
    st.markdown('<div class="eyebrow">EXECUTIVE DASHBOARD · READ-ONLY SERVICING</div>', unsafe_allow_html=True)
    st.title("Policy Servicing & Customer Support AI Agent")
    st.markdown(
        '<p class="subtle">Cross-references policy administration records, active endorsements, and customer/broker inquiries; '
        'uses RAG to answer coverage questions instantly with strict source attribution and refusal boundaries.</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-name">Active Policies</div><div class="metric-value">{len(all_policies)}</div><div class="metric-note">Read-only SQLite</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-name">Active Endorsements</div><div class="metric-value">{len(all_endorsements)}</div><div class="metric-note">Attached riders</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-name">Indexed Document Chunks</div><div class="metric-value">{len(store.chunks)}</div><div class="metric-note">PDF / DOCX / TXT</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-name">Refusal Threshold</div><div class="metric-value">{settings.min_retrieval_score}</div><div class="metric-note">Hallucination guard</div></div>', unsafe_allow_html=True)

    st.write("")
    left, right = st.columns([1.3, 1], gap="large")

    with left:
        st.subheader("Core Servicing Scenarios")
        st.caption("Click any pre-configured servicing scenario to test grounded question answering:")

        scenarios = [
            ("Maya Thompson", "POL-4821-AX", "Water Damage / Burst Pipe Coverage", "Is damage from a burst pipe covered and what deductible applies?", "Policyholder"),
            ("Ravi Patel", "POL-7710-QZ", "Commercial Auto / Vehicle Addition", "Can I add my new electric vehicle before the weekend?", "Broker"),
            ("Lena Ortiz", "POL-1193-KM", "Certificate of Insurance (COI)", "I need an updated certificate of insurance for my commercial landlord.", "Policyholder"),
            ("Maya Thompson", "POL-4821-AX", "Transactional Mutation Attempt (Safety Guardrail)", "Please cancel my policy immediately and process a refund.", "Policyholder"),
        ]

        for name, pol_num, topic, prompt_q, role in scenarios:
            badge_class = "role-broker" if role == "Broker" else "role-policyholder"
            with st.container():
                st.markdown(
                    f'<div class="card card-highlight">'
                    f'<span class="badge {badge_class}">{role}</span> '
                    f'<b>{name}</b> ({pol_num})<br>'
                    f'<span class="subtle"><b>Topic:</b> {topic}</span><br>'
                    f'<span style="font-size:0.77rem; color:#4a5450;">"{prompt_q}"</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"Launch Case: {name} - {topic[:24]}...", key=f"scen_{pol_num}_{topic}"):
                    st.session_state.policy_number = pol_num
                    st.session_state.messages = [{"role": "user", "content": prompt_q}]
                    agent = GroundedPolicyAgent(store, db_path, settings.top_k, settings.min_retrieval_score)
                    resp = agent.answer(prompt_q, pol_num)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": resp.answer,
                        "citations": [c.__dict__ for c in resp.citations],
                        "grounded": resp.grounded,
                        "is_mutation_refusal": resp.is_mutation_refusal,
                    })
                    st.session_state.selected_tab = "Conversations"
                    st.info("Scenario loaded into Conversations! Switch to the Conversations view in the sidebar.")

    with right:
        st.subheader("Architecture & Safety Boundaries")
        st.markdown("""
        <div class="card">
            <b>1. Read-Only Policy Administration Data</b>
            <p class="subtle">Direct SQL access strictly via parameterized <code>SELECT</code> statements over policyholders, policy terms, deductibles, and active endorsement riders. No write/update permissions.</p>
            <hr style="margin: 0.7rem 0;">
            <b>2. High-Precision Local RAG Pipeline</b>
            <p class="subtle">Document chunking with sliding overlap preserving source filename, section header, and page numbering. Deterministic embedding space ensures verifiable, reproducible cosine similarity search.</p>
            <hr style="margin: 0.7rem 0;">
            <b>3. Dual-Role Servicing (Policyholder vs Broker)</b>
            <p class="subtle">Tailors response detail and operational guidance depending on the account role: straightforward self-service next steps for policyholders; binding/issuance advisories for brokers.</p>
            <hr style="margin: 0.7rem 0;">
            <b>4. Zero-Hallucination & Mutation Guardrails</b>
            <p class="subtle">Refuses out-of-scope transactional requests (cancellations, claim approvals, policy alterations) and strictly declines answering when evidence falls below confidence threshold.</p>
        </div>
        """, unsafe_allow_html=True)


# =======================================================
# SECTION 2: CONVERSATIONS (CHAT WORKSPACE)
# =======================================================
elif section == "Conversations":
    st.markdown('<div class="eyebrow">SERVICING WORKSPACE · DUAL-ROLE CONVERSATIONAL AI</div>', unsafe_allow_html=True)
    st.title("Customer & Broker Servicing Workspace")
    st.markdown('<p class="subtle">Inspect policy administration facts, review active endorsements, and receive grounded answers backed by approved wording.</p>', unsafe_allow_html=True)

    queue_col, chat_col, details_col = st.columns([1.1, 1.8, 1.1], gap="large")

    demo_cases = [
        ("CS-2084", "Maya Thompson", "Water damage coverage", "Open", "POL-4821-AX", "Is damage from a burst pipe covered and what deductible applies?"),
        ("CS-2081", "Ravi Patel", "Adding a vehicle", "Waiting", "POL-7710-QZ", "Can I add my new electric vehicle before the weekend?"),
        ("CS-2077", "Lena Ortiz", "Certificate request", "Open", "POL-1193-KM", "I need an updated certificate of insurance."),
        ("CS-2075", "Jon Bell", "Deductible question", "Resolved", "POL-9032-RT", "How does the deductible apply to my renewal?"),
    ]

    with queue_col:
        st.subheader("Support Queue")
        search_query = st.text_input("Filter queue", placeholder="Name, policy #, topic", label_visibility="collapsed")
        status_filter = st.selectbox("Status Filter", ["All", "Open", "Waiting", "Resolved"], index=0)

        for case_id, name, topic, case_status, pol_num, question in demo_cases:
            if status_filter != "All" and status_filter != case_status:
                continue
            if search_query and search_query.lower() not in f"{case_id} {name} {topic} {pol_num}".lower():
                continue

            active_border = "border-left: 3px solid #0d655b;" if st.session_state.get("policy_number") == pol_num else ""
            st.markdown(
                f'<div class="case" style="{active_border}">'
                f'<span class="case-meta">{case_id}</span>'
                f'<span class="case-name">{name}</span><br>'
                f'<span class="case-topic">{topic} · <code>{pol_num}</code></span><br>'
                f'<div style="margin-top:0.35rem;"><span class="badge {case_status.lower()}">{case_status}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Load Case {case_id}", key=f"load_{case_id}", use_container_width=True):
                st.session_state.policy_number = pol_num
                st.session_state.messages = [{"role": "user", "content": question}]
                agent = GroundedPolicyAgent(store, db_path, settings.top_k, settings.min_retrieval_score)
                resp = agent.answer(question, pol_num)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": resp.answer,
                    "citations": [c.__dict__ for c in resp.citations],
                    "grounded": resp.grounded,
                    "is_mutation_refusal": resp.is_mutation_refusal,
                })
                st.rerun()

    with chat_col:
        current_pol_num = st.session_state.get("policy_number", "POL-4821-AX")
        current_policy = find_policy(current_pol_num, db_path)

        if not current_policy:
            st.error(f"Policy {current_pol_num} not found.")
            st.stop()

        role = current_policy.get("role", "policyholder")
        role_badge_class = "role-broker" if role == "broker" else "role-policyholder"

        st.subheader(f"{current_policy['customer_name']}")
        st.markdown(
            f'<span><code>{current_policy["policy_number"]}</code> · {current_policy["product"]} · '
            f'<span class="badge {role_badge_class}">{role.upper()}</span> · '
            f'<span class="badge open">{current_policy["status"]}</span></span>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="card" style="margin-top:0.6rem; padding:0.8rem 1rem;">'
            f'<span class="subtle">Effective: <b>{current_policy["effective_date"]}</b> to <b>{current_policy["expiration_date"]}</b> &nbsp;|&nbsp; '
            f'Deductible: <b>{current_policy["deductible"]}</b> &nbsp;|&nbsp; Premium: <b>{current_policy["annual_premium"]}</b></span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Render conversation
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant":
                    if msg.get("is_mutation_refusal"):
                        st.markdown('<div class="refusal-label">⚠️ READ-ONLY SERVICING GUARDRAIL TRIGGERED</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="refusal-box">{msg["content"]}</div>', unsafe_allow_html=True)
                    elif msg.get("grounded", True):
                        st.markdown('<div class="answer-label">🛡️ GROUNDED RESPONSE · POLICY ADMIN & APPROVED DOCUMENTS</div>', unsafe_allow_html=True)
                        st.write(msg["content"])
                        if msg.get("citations"):
                            st.markdown("<br><span class='eyebrow'>VERIFIED CITATIONS</span>", unsafe_allow_html=True)
                            for cit in msg["citations"]:
                                page_txt = f", Page {cit['page']}" if cit.get('page') else ""
                                st.markdown(
                                    f'<span class="source-pill">📄 <b>{cit["source"]}</b>{page_txt} '
                                    f'<small>(match: {cit["score"]:.2f})</small></span>',
                                    unsafe_allow_html=True,
                                )
                    else:
                        st.write(msg["content"])
                else:
                    st.write(msg["content"])

        # Quick test prompts
        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        st.caption("Quick inquiry samples:")
        quick_cols = st.columns(3)
        with quick_cols[0]:
            if st.button("💧 Water & Backup Terms", use_container_width=True):
                st.session_state.temp_prompt = "Is damage from a burst pipe or water backup covered, and what deductible applies?"
                st.rerun()
        with quick_cols[1]:
            if st.button("🚗 Newly Acquired Auto", use_container_width=True):
                st.session_state.temp_prompt = "Can I add a newly acquired vehicle and how many days do I have to report it?"
                st.rerun()
        with quick_cols[2]:
            if st.button("🚫 Transactional Mutation Test", use_container_width=True):
                st.session_state.temp_prompt = "Please cancel my policy immediately and issue a refund to my credit card."
                st.rerun()

        prompt = st.chat_input("Ask a policy, endorsement, or coverage question...")
        if not prompt and "temp_prompt" in st.session_state:
            prompt = st.session_state.pop("temp_prompt")

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            agent = GroundedPolicyAgent(store, db_path, settings.top_k, settings.min_retrieval_score)
            response = agent.answer(prompt, current_pol_num)
            st.session_state.messages.append({
                "role": "assistant",
                "content": response.answer,
                "citations": [c.__dict__ for c in response.citations],
                "grounded": response.grounded,
                "is_mutation_refusal": response.is_mutation_refusal,
            })
            st.rerun()

    with details_col:
        st.subheader("Policy Record")
        st.markdown(
            f'<div class="card">'
            f'<div class="eyebrow">NAMED INSURED</div>'
            f'<b>{current_policy["customer_name"]}</b><br>'
            f'<span class="subtle">{current_policy["email"]}</span><hr style="margin:0.6rem 0;">'
            f'<div class="eyebrow">RISK LOCATION</div>'
            f'<span class="subtle">{current_policy["property_address"]}</span><hr style="margin:0.6rem 0;">'
            f'<div class="eyebrow">COVERAGE SPECIFICS</div>'
            f'<span class="subtle">Annual Premium: <b>{current_policy["annual_premium"]}</b><br>'
            f'Deductible: <b>{current_policy["deductible"]}</b></span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.subheader("Active Endorsements")
        policy_endorsements = list_endorsements(current_policy["id"], db_path)
        if policy_endorsements:
            for end in policy_endorsements:
                st.markdown(
                    f'<div class="card">'
                    f'<b>{end["title"]}</b> <span class="badge open">{end["endorsement_number"]}</span><br>'
                    f'<span class="subtle">Limit: <b>{end["limit_value"]}</b> · Effective {end["effective_date"]}</span>'
                    f'<p style="font-size:0.75rem; color:#5c6863; margin-top:0.4rem;">{end["summary"]}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No endorsement riders attached to this policy.")


# =======================================================
# SECTION 3: POLICIES EXPLORER
# =======================================================
elif section == "Policies":
    st.markdown('<div class="eyebrow">POLICY ADMINISTRATION SYSTEM · READ-ONLY DIRECTORY</div>', unsafe_allow_html=True)
    st.title("Policy Administration Records")
    st.markdown('<p class="subtle">Browse all insured accounts, coverage schedules, and attached endorsement riders retrieved directly from the policy administration database.</p>', unsafe_allow_html=True)

    filter_text = st.text_input("Search policies by number, insured name, or product line", placeholder="Type to filter...")
    
    filtered_policies = search_policies(filter_text, db_path) if filter_text else all_policies

    st.write(f"Found **{len(filtered_policies)}** matching policy records:")

    for pol in filtered_policies:
        role = pol.get("role", "policyholder")
        role_class = "role-broker" if role == "broker" else "role-policyholder"
        pol_id = pol.get("id") or find_policy(pol["policy_number"], db_path)["id"]
        endorsements = list_endorsements(pol_id, db_path)

        if endorsements:
            end_labels = [f"{e['title']} ({e['endorsement_number']}: {e['limit_value']})" for e in endorsements]
            end_display = ", ".join(end_labels)
        else:
            end_display = "None"

        risk_addr = pol.get("property_address") or "Listed in policy schedule"

        with st.container():
            p_col1, p_col2 = st.columns([3.5, 1])
            with p_col1:
                st.markdown(
                    f'<div class="card">'
                    f'<span class="badge {role_class}">{role.upper()}</span> '
                    f'<b>{pol["policy_number"]}</b> &nbsp;—&nbsp; <b>{pol["customer_name"]}</b> ({pol["product"]})<br>'
                    f'<span class="subtle">Term: {pol["effective_date"]} to {pol["expiration_date"]} &nbsp;|&nbsp; '
                    f'Deductible: {pol["deductible"]} &nbsp;|&nbsp; Premium: {pol["annual_premium"]}</span><br>'
                    f'<span class="subtle">Risk Address: {risk_addr}</span><br>'
                    f'<div style="margin-top:0.5rem; font-size:0.75rem; color:#235347;">'
                    f'<b>Attached Endorsements:</b> {end_display}'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with p_col2:
                if st.button("Open in Servicing Chat", key=f"btn_{pol['policy_number']}", use_container_width=True):
                    st.session_state.policy_number = pol["policy_number"]
                    st.session_state.messages = []
                    st.success(f"Switched to {pol['policy_number']}! Navigate to Conversations in sidebar.")


# =======================================================
# SECTION 4: KNOWLEDGE BASE & RAG EXPLORER
# =======================================================
elif section == "Knowledge base":
    st.markdown('<div class="eyebrow">RETRIEVAL-AUGMENTED GENERATION · DOCUMENT INSPECTOR</div>', unsafe_allow_html=True)
    st.title("Policy Document Corpus & Vector Store")
    st.markdown('<p class="subtle">Inspect approved insurance policy documents, test real-time similarity search against local vector embeddings, and inspect chunk metadata.</p>', unsafe_allow_html=True)

    kb_col1, kb_col2 = st.columns([1, 1.3], gap="large")

    with kb_col1:
        st.subheader("Approved Source Documents")
        doc_files = list(settings.documents_dir.glob("*.*"))
        for doc in doc_files:
            size_kb = doc.stat().st_size / 1024
            matching_chunks = [c for c in store.chunks if c.source == doc.name]
            st.markdown(
                f'<div class="card">'
                f'<b>📄 {doc.name}</b><br>'
                f'<span class="subtle">Size: {size_kb:.1f} KB · Indexed Chunks: <b>{len(matching_chunks)}</b> · Format: <code>{doc.suffix.lstrip(".")}</code></span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.write("")
        st.subheader("Vector Store Metrics")
        st.markdown(
            f'<div class="card">'
            f'<span class="subtle">Total Indexed Chunks: <b>{len(store.chunks)}</b><br>'
            f'Embedding Dimension: <b>{store.dimensions}</b>-d normalized hash vectors<br>'
            f'Persistence Location: <code>{settings.vector_store_path}</code><br>'
            f'Default Retrieval Top-K: <b>{settings.top_k}</b><br>'
            f'Similarity Refusal Threshold: <b>{settings.min_retrieval_score}</b></span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with kb_col2:
        st.subheader("RAG Similarity Search Sandbox")
        st.caption("Test how policyholder inquiries match against the indexed chunks:")
        test_q = st.text_input("Test query", value="water backup sewer drain overflow limit", label_visibility="collapsed")
        test_score = st.slider("Min score threshold", min_value=0.01, max_value=0.40, value=settings.min_retrieval_score, step=0.01)

        if test_q:
            results = retrieve(test_q, store, top_k=5, min_score=test_score)
            if results.has_evidence:
                st.success(f"Retrieved {len(results.results)} matching chunk(s) above threshold {test_score:.2f}")
                for idx, res in enumerate(results.results, 1):
                    page_info = f", Page {res.chunk.page}" if res.chunk.page else ""
                    st.markdown(
                        f'<div class="doc-chunk">'
                        f'<div class="doc-meta"><b>#{idx} · {res.chunk.source}{page_info}</b> · Score: <b>{res.score:.3f}</b> · Chunk ID: <code>{res.chunk.chunk_id}</code></div>'
                        f'<div style="font-size:0.83rem; line-height:1.45;">{res.chunk.text}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.warning(f"No document chunks scored above {test_score:.2f}. Agent would trigger refusal response.")

st.divider()
st.caption(f"Session: {st.session_state.user.username} · Role: {st.session_state.user.role} · Low-Risk Read-Only Servicing Deployment · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
