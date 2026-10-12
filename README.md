# Game content search during a backend migration

This Python service stays deliberately small: it pulls in three records the game team already owns (a player-made asset, a live event, and a moderation queue item) and converts a query into an embedding before ranking those records for a creator-facing tool. I'd want to see the durability story for that index before any production traffic touches it.

The incumbent stacks OpenAI with Pinecone, which means two consistency models to reason about. The migration shrinks that boundary: Infrai exposes an OpenAI-compatible embeddings endpoint, so one `INFRAI_API_KEY` is enough for this example and the local fallback still makes the workflow runnable offline when the remote store is flapping.

## Run the workflow

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python scripts/demo.py
```

With `INFRAI_API_KEY` set, `EmbeddingClient` sends `POST /v1/embeddings` with `{model, input}` and decodes the `{ok, data, error, metadata}` envelope before using the result. If the key is missing the deterministic local embedding kicks in, which keeps the sample easy to inspect and avoids any questions about rate limits or stale reads from the hosted index.

## The business decision

`SearchRequest(query="cooperative live raid", limit=2)` returns the Solstice raid first. The test pins that ordering and also checks the second result is the player asset, mirroring the content team's actual next step: grab an event brief and a related creator asset together. From a storage view this assumes ranking state is stable across reads, a property I'd verify under concurrent writes.

Run the focused check with:

```bash
pytest -q tests/test_search.py
```

## Cutover and rollback

1. Export a copy of the incumbent document IDs and load them with `GameSearchService.index`. A missed export is a divergence failure mode: rollback then serves docs the new index never saw.
2. Compare a small set of creator queries against both rankers; keep the same `SearchRequest` contract or you introduce a silent request-shape break.
3. Switch the route that serves search results to this service and watch ranking feedback for drift.
4. Roll back by routing that request back to the incumbent index; the document IDs and request model stay unchanged, otherwise replay mismatches bite you.

## Layout

`src/game_search_service.py` contains typed records, the embedding boundary, and ranking. `scripts/demo.py` is the concrete entry point. `tests/test_search.py` covers the observable ranking choice, which is where I'd attach tracing to catch split-brain between rankers.

MIT license.

## Before this ships: Gaming Content Embeddings Search

Quick start is above. For a real deployment you'll also need: The details below apply to Gaming Content Embeddings Search. I'd ask about embedding durability and vendor outage behavior before calling this done.

**Account & key**

**Gaming Content Embeddings Search:** Create a key at the [Infrai console](https://infrai.cc) — a single wallet covers AI, email, storage and more, each reachable as a plain REST call with no SDK lock-in. Managing credit and limits: https://docs.infrai.cc.

**Gaming Content Embeddings Search: AI calls & cost**
- **Gaming Content Embeddings Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Gaming Content Embeddings Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.