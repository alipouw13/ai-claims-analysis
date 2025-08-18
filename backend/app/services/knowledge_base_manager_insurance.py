import logging
from typing import List, Dict, Optional

from app.core.config import settings
from app.services.azure_services import AzureServiceManager

logger = logging.getLogger(__name__)

class InsuranceKnowledgeBaseManager:
    """Policy/Claims knowledge base manager that mirrors the financial KB manager but targets insurance indexes.

    - Uses simple query (no semantic rank) for policy and claims indexes
    - Normalizes vector schema fields (id, parent_id, content, title, source, processed_at)
    - Provides helpers for field filtering (policy_number, claim_id)
    """

    def __init__(self, azure_manager: AzureServiceManager):
        self.azure_manager = azure_manager

    async def search_knowledge_base(
        self,
        query: str,
        filters: Optional[Dict] = None,
        top_k: int = 10,
        token_tracker=None,
        tracking_id: Optional[str] = None,
    ) -> List[Dict]:
        # Compose filter string for simple search
        filter_str = None
        try:
            if filters:
                clauses = []
                if filters.get("policy_number"):
                    clauses.append(f"policy_number eq '{filters['policy_number']}'")
                if filters.get("claim_id"):
                    clauses.append(f"claim_id eq '{filters['claim_id']}'")
                filter_str = " and ".join(clauses) if clauses else None
        except Exception:
            filter_str = None

        # Force simple query for insurance indexes; no semantic, no vector queries
        results: List[Dict] = []
        for index_name in [
            getattr(settings, 'AZURE_SEARCH_POLICY_INDEX_NAME', None),
            getattr(settings, 'AZURE_SEARCH_CLAIMS_INDEX_NAME', None),
        ]:
            if not index_name:
                continue
            try:
                client = self.azure_manager.get_search_client_for_index(index_name)
                # best-effort select; fall back if needed
                try:
                    paged = await client.search(
                        search_text=query,
                        top=top_k,
                        filter=filter_str,
                        query_type="simple",
                        select=["id", "parent_id", "content", "title", "source", "processed_at", "credibility_score", "page_number"],
                    )
                except Exception:
                    paged = await client.search(
                        search_text=query,
                        top=top_k,
                        filter=filter_str,
                        query_type="simple",
                    )
                async for r in paged:
                    rd = dict(r)
                    # Normalize content key for backward compatibility
                    if 'chunk' in rd and 'content' not in rd:
                        rd['content'] = rd['chunk']
                    # Ensure we have the standard field names
                    if 'id' not in rd and 'chunk_id' in rd:
                        rd['id'] = rd['chunk_id']
                    results.append(rd)
            except Exception as e:
                logger.warning(f"Insurance KB search failed for index {index_name}: {e}")

        # Deduplicate by key preference
        best_by_id: Dict[str, Dict] = {}
        for item in results:
            key = item.get('id') or item.get('chunk_id') or item.get('parent_id')
            if not key:
                key = f"auto_{len(best_by_id)+1}"
            if key not in best_by_id:
                best_by_id[key] = item

        return list(best_by_id.values())[:top_k]

