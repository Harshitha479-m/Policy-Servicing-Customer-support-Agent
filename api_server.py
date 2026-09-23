from __future__ import annotations

import json
import logging
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.agent import GroundedPolicyAgent
from app.auth import authenticate
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

TOKENS: dict[str, dict[str, str]] = {}


def get_store() -> LocalVectorStore:
    seed_demo_data(settings.database_path())
    if settings.vector_store_path.exists():
        try:
            return LocalVectorStore.load(settings.vector_store_path)
        except Exception:
            logger.warning("Could not load vector store; rebuilding it")
    store = LocalVectorStore.build(ingest_directory(settings.documents_dir))
    try:
        store.save(settings.vector_store_path)
    except OSError:
        logger.warning("Could not persist vector store")
    return store


STORE = get_store()
DB_PATH = settings.database_path()
AGENT = GroundedPolicyAgent(STORE, DB_PATH, settings.top_k, settings.min_retrieval_score)


def serialize_response(response) -> dict:
    return {
        "answer": response.answer,
        "citations": [citation.__dict__ for citation in response.citations],
        "grounded": response.grounded,
        "policy": response.policy,
        "is_mutation_refusal": response.is_mutation_refusal,
    }


def documents() -> list[dict]:
    items = []
    for path in sorted(settings.documents_dir.glob("*.*")):
        items.append({
            "name": path.name,
            "format": path.suffix.lstrip("."),
            "size_kb": round(path.stat().st_size / 1024, 1),
            "chunks": sum(chunk.source == path.name for chunk in STORE.chunks),
        })
    return items


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "PolicySupportApi/1.0"

    def log_message(self, format: str, *args) -> None:
        logger.info("%s - %s", self.address_string(), format % args)

    def _send(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload).encode("utf-8")
        origin = self.headers.get("Origin", "")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if origin in {"http://localhost:5173", "http://127.0.0.1:5173"}:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Session-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def _authorized(self) -> bool:
        token = self.headers.get("X-Session-Token", "")
        return token in TOKENS

    def do_OPTIONS(self) -> None:
        self._send(204, {})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._body()
        if path == "/api/auth/login":
            user = authenticate(
                str(body.get("username", "")),
                str(body.get("password", "")),
                settings.demo_username,
                settings.demo_password,
            )
            if not user:
                self._send(401, {"error": "Invalid credentials."})
                return
            token = secrets.token_urlsafe(32)
            TOKENS[token] = {"username": user.username, "role": user.role}
            self._send(200, {"token": token, "user": TOKENS[token]})
            return
        if not self._authorized():
            self._send(401, {"error": "Your session is not authorized."})
            return
        if path == "/api/auth/logout":
            TOKENS.pop(self.headers.get("X-Session-Token", ""), None)
            self._send(200, {"ok": True})
            return
        if path == "/api/chat":
            question = str(body.get("question", "")).strip()
            policy_number = str(body.get("policy_number", "")).strip()
            if not question or not policy_number:
                self._send(400, {"error": "A question and policy number are required."})
                return
            self._send(200, serialize_response(AGENT.answer(question, policy_number)))
            return
        self._send(404, {"error": "Not found."})

    def do_GET(self) -> None:
        if not self._authorized():
            self._send(401, {"error": "Your session is not authorized."})
            return
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        if path == "/api/bootstrap":
            policies = list_policies(DB_PATH)
            self._send(200, {
                "policies": policies,
                "endorsements": list_all_endorsements(DB_PATH),
                "documents": documents(),
                "metrics": {
                    "policies": len(policies),
                    "endorsements": len(list_all_endorsements(DB_PATH)),
                    "chunks": len(STORE.chunks),
                    "threshold": settings.min_retrieval_score,
                },
                "settings": {"top_k": settings.top_k, "threshold": settings.min_retrieval_score},
            })
            return
        if path == "/api/policies":
            query = params.get("q", [""])[0]
            self._send(200, search_policies(query, DB_PATH) if query else list_policies(DB_PATH))
            return
        if path.startswith("/api/policies/"):
            policy = find_policy(path.rsplit("/", 1)[-1], DB_PATH)
            if not policy:
                self._send(404, {"error": "Policy not found."})
                return
            policy["endorsements"] = list_endorsements(policy["id"], DB_PATH)
            self._send(200, policy)
            return
        if path == "/api/knowledge/search":
            query = params.get("q", [""])[0]
            try:
                threshold = float(params.get("threshold", [str(settings.min_retrieval_score)])[0])
            except ValueError:
                self._send(400, {"error": "Threshold must be numeric."})
                return
            results = retrieve(query, STORE, top_k=5, min_score=threshold) if query else None
            self._send(200, {
                "has_evidence": bool(results and results.has_evidence),
                "results": [
                    {"source": result.chunk.source, "page": result.chunk.page, "score": result.score,
                     "chunk_id": result.chunk.chunk_id, "text": result.chunk.text}
                    for result in (results.results if results else [])
                ],
            })
            return
        self._send(404, {"error": "Not found."})


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), ApiHandler)
    logger.info("API server listening on http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
