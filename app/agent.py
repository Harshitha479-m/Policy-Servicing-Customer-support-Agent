from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.db import find_policy, list_endorsements
from app.retrieval import RetrievedContext, retrieve
from app.vector_store import LocalVectorStore

logger = logging.getLogger(__name__)

REFUSAL = "I cannot verify that from the approved policy documents and policy administration data available to me. I will not guess about coverage or invent a clause. Please route this question to a licensed specialist."

MUTATION_KEYWORDS = (
    "cancel my policy",
    "cancel policy",
    "cancellation",
    "change my address",
    "update address",
    "file a claim",
    "file claim",
    "submit a claim",
    "approve claim",
    "pay claim",
    "bind coverage",
    "bind policy",
    "increase my limit",
    "lower my deductible",
    "charge my card",
    "refund my premium",
)

MUTATION_REFUSAL = (
    "This agent operates strictly within a low-risk, read-only servicing scope. "
    "It cannot modify policy terms, process cancellations, change policyholder addresses, "
    "bind endorsements, or make claims settlement decisions. "
    "To execute this transaction, please contact your authorized servicing representative or underwriting department."
)


@dataclass(frozen=True)
class Citation:
    source: str
    page: int | None
    score: float


@dataclass(frozen=True)
class AgentResponse:
    answer: str
    citations: list[Citation]
    grounded: bool
    policy: dict | None
    is_mutation_refusal: bool = False


class GroundedPolicyAgent:
    def __init__(self, store: LocalVectorStore, db_path: Path, top_k: int = 5, min_score: float = 0.08):
        self.store = store
        self.db_path = db_path
        self.top_k = top_k
        self.min_score = min_score

    def is_mutation_request(self, question: str) -> bool:
        lower = question.lower()
        return any(keyword in lower for keyword in MUTATION_KEYWORDS)

    def answer(self, question: str, policy_number: str) -> AgentResponse:
        policy = find_policy(policy_number, self.db_path)
        if not policy:
            return AgentResponse("I could not find that policy in the read-only administration data.", [], False, None)

        if self.is_mutation_request(question):
            logger.info("Mutation request intercepted for policy=%s question=%s", policy_number, question[:100])
            return AgentResponse(MUTATION_REFUSAL, [], False, policy, is_mutation_refusal=True)

        context = retrieve(question, self.store, self.top_k, self.min_score)
        if not context.has_evidence:
            logger.info("No evidence for policy=%s question=%s", policy_number, question[:120])
            return AgentResponse(REFUSAL, [], False, policy)

        answer = self._compose_answer(question, policy, context)
        citations = [Citation(result.chunk.source, result.chunk.page, result.score) for result in context.results]
        return AgentResponse(answer, citations, True, policy)

    def _compose_answer(self, question: str, policy: dict, context: RetrievedContext) -> str:
        excerpts = " ".join(result.chunk.text for result in context.results[:3])
        lower = question.lower()
        endorsements = list_endorsements(policy["id"], self.db_path)
        role = policy.get("role", "policyholder")

        facts = [
            f"Policy {policy['policy_number']} is {policy['status']} ({policy['product']})",
            f"Named Insured: {policy['customer_name']}",
            f"Effective Term: {policy['effective_date']} to {policy['expiration_date']}",
            f"Listed Deductible: {policy['deductible']}",
        ]
        base_record = f"The administration record shows {facts[0]} for {policy['customer_name']}, effective {facts[2]}, with a listed deductible of {policy['deductible']}."

        # Case 1: Burst pipe / Water damage / Water backup
        if any(term in lower for term in ("water", "pipe", "backup", "sewer", "drain", "flood")):
            matching_end = next((e for e in endorsements if "water" in e["title"].lower() or "backup" in e["title"].lower()), None)
            end_fact = (
                f" The database also lists active Endorsement {matching_end['endorsement_number']} ({matching_end['title']}) with a {matching_end['limit_value']} limit."
                if matching_end else ""
            )
            return (
                f"{base_record}{end_fact} Based on the approved policy wording: {excerpts} "
                f"Please note that sudden and accidental plumbing discharge is subject to the standard {policy['deductible']} deductible, "
                f"while sewer or drain backup is governed by the endorsement limit."
            )

        # Case 2: Vehicle addition / Newly acquired autos (Commercial Auto)
        if any(term in lower for term in ("vehicle", "car", "truck", "auto", "electric", "add a vehicle", "newly acquired")):
            hired_end = next((e for e in endorsements if "auto" in e["title"].lower() or "hired" in e["title"].lower()), None)
            end_text = f" Additionally, active endorsement {hired_end['endorsement_number']} ({hired_end['title']}) provides {hired_end['limit_value']} for hired/non-owned autos." if hired_end else ""
            role_note = " As an authorized broker, you may initiate the formal vehicle schedule addition through your portal." if role == "broker" else " You should submit the vehicle details (VIN and purchase date) to your broker within 14 days."
            return (
                f"{base_record}{end_text} Under the approved Commercial Auto terms: {excerpts} "
                f"Newly acquired autos receive temporary coverage for up to 14 days with the broadest coverage currently on the schedule, subject to timely notification.{role_note}"
            )

        # Case 3: Certificate of Insurance (COI) requests
        if any(term in lower for term in ("certificate", "coi", "proof of insurance", "cert")):
            role_note = " As an authorized broker, you can issue standard certificates reflecting these in-force terms." if role == "broker" else " A standard Certificate of Insurance can be generated for your business partners confirming current active status."
            return (
                f"{base_record} Regarding your certificate request: {excerpts} "
                f"This policy is in force with an annual premium of {policy['annual_premium']} and {policy['deductible']} deductible.{role_note} "
                f"Note that certificates confirm coverage in force but do not modify policy terms."
            )

        # Case 4: Deductible inquiry
        if any(term in lower for term in ("deduct", "out of pocket")):
            end_names = [f"Endorsement {e['endorsement_number']} ({e['title']})" for e in endorsements]
            end_summary = f" Active endorsements on this policy: {', '.join(end_names)}." if end_names else ""
            return (
                f"{base_record}{end_summary} Under the approved policy documents: {excerpts} "
                f"The deductible applies once per covered occurrence unless modified by an applicable endorsement schedule."
            )

        # Case 5: Business Interruption / Loss of Income
        if any(term in lower for term in ("business income", "interruption", "restoration", "lost income", "revenue")):
            bi_end = next((e for e in endorsements if "income" in e["title"].lower() or "business" in e["title"].lower()), None)
            end_text = f" The policy includes active Endorsement {bi_end['endorsement_number']} ({bi_end['title']}) with a {bi_end['limit_value']} limit." if bi_end else ""
            return (
                f"{base_record}{end_text} Based on the retrieved endorsement terms: {excerpts} "
                f"Business income coverage commences 72 hours following direct physical damage, while extra expense applies immediately."
            )

        # Default grounded response
        end_info = f" Active endorsements: {', '.join(e['title'] for e in endorsements)}." if endorsements else ""
        return f"{base_record}{end_info} The approved document context states: {excerpts}"

