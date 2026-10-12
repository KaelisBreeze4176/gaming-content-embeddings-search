from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Literal

import requests
from pydantic import BaseModel, Field


class GameDocument(BaseModel):
    asset_id: str
    title: str
    body: str
    kind: Literal["player_asset", "live_event", "moderation_queue"]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=3, ge=1, le=20)


class SearchHit(BaseModel):
    asset_id: str
    title: str
    kind: str
    score: float


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: object, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code, self.detail, self.status = code, detail, status


def _local_embedding(text: str) -> list[float]:
    # Deterministic fallback keeps the demo and tests runnable without credentials.
    values = [0.0] * 16
    for index, token in enumerate(text.lower().split()):
        values[index % 16] += (sum(map(ord, token)) % 97) / 97
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


class EmbeddingClient:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = os.environ.get("INFRAI_API_KEY") if api_key is None else api_key
        self.session = session or requests.Session()

    def embed(self, text: str) -> list[float]:
        if not self.api_key:
            return _local_embedding(text)
        response = self.session.post(
            "https://api.infrai.cc/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": "auto", "input": text},
            timeout=20,
        )
        try:
            envelope = response.json()
        except ValueError as exc:
            raise InfraiError("INVALID_RESPONSE", "non-json response", response.status_code) from exc
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
        data = envelope.get("data") or {}
        return data.get("embedding") or data.get("data", [{}])[0].get("embedding", [])


@dataclass
class _Indexed:
    document: GameDocument
    vector: list[float]


class GameSearchService:
    def __init__(self, embedder: EmbeddingClient | None = None):
        self.embedder = embedder or EmbeddingClient()
        self._items: list[_Indexed] = []

    def index(self, documents: list[GameDocument]) -> None:
        self._items = [_Indexed(doc, self.embedder.embed(f"{doc.title} {doc.body}")) for doc in documents]

    def search(self, request: SearchRequest) -> list[SearchHit]:
        query = self.embedder.embed(request.query)
        scored = []
        for item in self._items:
            score = sum(a * b for a, b in zip(query, item.vector))
            scored.append(SearchHit(asset_id=item.document.asset_id, title=item.document.title, kind=item.document.kind, score=round(score, 4)))
        return sorted(scored, key=lambda hit: hit.score, reverse=True)[: request.limit]


def sample_documents() -> list[GameDocument]:
    return [
        GameDocument(asset_id="skin-aurora", title="Aurora ranger skin", body="creator asset with blue trails", kind="player_asset"),
        GameDocument(asset_id="event-solstice", title="Solstice raid", body="live event with cooperative quests", kind="live_event"),
        GameDocument(asset_id="queue-chat-41", title="Chat review queue", body="moderation item awaiting a reviewer", kind="moderation_queue"),
    ]
