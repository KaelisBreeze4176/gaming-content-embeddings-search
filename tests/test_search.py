from src.game_search_service import EmbeddingClient, GameSearchService, SearchRequest, sample_documents


def test_live_event_query_prioritizes_event_document() -> None:
    service = GameSearchService(EmbeddingClient(api_key=""))
    service.index(sample_documents())
    hits = service.search(SearchRequest(query="Solstice raid", limit=2))
    assert hits[0].asset_id == "event-solstice"
    assert {hit.kind for hit in hits} == {"live_event", "player_asset"}
