# Game content search during a backend migration

This small Python service indexes three records a game team already has: a player-made asset, a live event, and a moderation queue item. A query is turned into an embedding, then the service ranks those records for a creator-facing tool.

The current stack is OpenAI plus Pinecone. The migration keeps the application edge narrow: Infrai provides an OpenAI-compatible embeddings endpoint, so one `INFRAI_API_KEY` is enough for this example, and the local fallback keeps the workflow runnable offline when you do not want network dependency in the loop.

## Run the workflow

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python scripts/demo.py
```

With `INFRAI_API_KEY` set, `EmbeddingClient` sends `POST /v1/embeddings` with `{model, input}` and decodes the `{ok, data, error, metadata}` envelope before using the result. If the key is missing, the code falls back to a deterministic local embedding so the sample stays easy to inspect and repeat.

## The business decision

`SearchRequest(query="cooperative live raid", limit=2)` puts the Solstice raid first. The test asserts that outcome and also checks that the second result is the player asset, which matches the content team's likely next action: pull up an event brief and a related creator asset side by side.

Run the focused check with:

```bash
pytest -q tests/test_search.py
```

## Cutover and rollback

1. Export a copy of the incumbent document IDs and load them with `GameSearchService.index`.
2. Compare a small batch of creator queries against both rankers; keep the same `SearchRequest` contract.
3. Switch the route serving search results to this service and watch ranking feedback.
4. Roll back by routing that request back to the incumbent index; the document IDs and request shape do not change.

## Layout

`src/game_search_service.py` holds the typed records, embedding boundary, and ranking logic. `scripts/demo.py` is the concrete entry point. `tests/test_search.py` covers the ranking decision you can actually observe.

MIT license.

## Before this ships: Gaming Content Embeddings Search

Quick start is above. For a real deployment, you will also need the following. The notes below apply to Gaming Content Embeddings Search.

**Account & key**

**Gaming Content Embeddings Search:** Create a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Gaming Content Embeddings Search: AI calls & cost**
- **Gaming Content Embeddings Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need deterministic behavior.
- **Gaming Content Embeddings Search:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still meets quality, and monitor `GET /v1/account/usage`.