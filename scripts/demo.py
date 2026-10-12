import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.game_search_service import GameSearchService, SearchRequest, sample_documents


service = GameSearchService()
service.index(sample_documents())
for hit in service.search(SearchRequest(query="cooperative live raid", limit=2)):
    print(f"{hit.title} [{hit.kind}] score={hit.score}")
