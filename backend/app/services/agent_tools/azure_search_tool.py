"""
Azure AI Search Tool for Azure AI Foundry Agents

This tool provides Azure AI Search functionality to agents, allowing them to:
- Search across multiple indexes (policy, claims, financial documents)
- Perform hybrid search (vector + keyword + semantic)
- Retrieve relevant documents and chunks
- Support agentic retrieval with query planning

Based on Azure AI Foundry documentation:
https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/azure-ai-search?tabs=pythonsdk
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from azure.ai.ml.entities import AzureAISearchConnection
    from azure.ai.ml import MLClient
    from azure.identity import DefaultAzureCredential
    AZURE_AI_ML_AVAILABLE = True
except ImportError:
    AZURE_AI_ML_AVAILABLE = False
    logger.warning("Azure AI ML SDK not available, using mock implementation")

from app.core.config import settings
from app.services.azure_services import AzureServiceManager

class AzureSearchTool:
    """
    Azure AI Search tool for Azure AI Foundry agents
    
    This tool can be attached to agents to provide:
    - Document search across multiple indexes
    - Hybrid search capabilities
    - Policy and claims document retrieval
    - Financial document search
    """
    
    def __init__(self, connection_name: str = None):
        self.connection_name = connection_name or "azure-search-connection"
        self.azure_manager = None
        self.search_client = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the Azure Search tool"""
        try:
            if not AZURE_AI_ML_AVAILABLE:
                logger.warning("Azure AI ML SDK not available, using mock Azure Search tool")
                return
                
            # Initialize Azure Service Manager
            self.azure_manager = AzureServiceManager()
            await self.azure_manager.initialize()
            
            # Create Azure AI Search connection if needed
            await self._create_connection()
            
            self._initialized = True
            logger.info(f"Azure Search tool initialized with connection: {self.connection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Search tool: {e}")
            raise
    
    async def _create_connection(self):
        """Create Azure AI Search connection for the agent"""
        try:
            # Check if connection already exists
            ml_client = MLClient(
                credential=DefaultAzureCredential(),
                subscription_id=settings.AZURE_SUBSCRIPTION_ID,
                resource_group_name=settings.AZURE_AI_FOUNDRY_RESOURCE_GROUP,
                workspace_name=settings.AZURE_AI_FOUNDRY_WORKSPACE_NAME
            )
            
            # Create connection configuration
            connection = AzureAISearchConnection(
                name=self.connection_name,
                endpoint=settings.AZURE_AI_SEARCH_ENDPOINT,
                api_key=settings.AZURE_SEARCH_API_KEY
            )
            
            # Create or update the connection
            ml_client.connections.create_or_update(connection)
            logger.info(f"Azure AI Search connection '{self.connection_name}' created/updated")
            
        except Exception as e:
            logger.error(f"Failed to create Azure AI Search connection: {e}")
            # Continue without connection - tool will still work with direct Azure Search access
    
    async def search_documents(
        self, 
        query: str, 
        index_type: str = "all",
        top_k: int = 10,
        filters: str = None,
        search_type: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        Search documents across Azure AI Search indexes
        
        Args:
            query: Search query
            index_type: "policy", "claims", "financial", or "all"
            top_k: Number of results to return
            filters: OData filter expression
            search_type: "simple", "semantic", "vector", or "hybrid"
            
        Returns:
            Search results with documents and metadata
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Determine which indexes to search
            indexes = self._get_indexes_for_type(index_type)
            
            all_results = []
            for index_name in indexes:
                try:
                    # Perform search on this index
                    results = await self.azure_manager.hybrid_search(
                        query=query,
                        top_k=top_k,
                        filters=filters,
                        index_name=index_name
                    )
                    
                    # Add index metadata to results
                    for result in results:
                        result["index_name"] = index_name
                        result["index_type"] = self._get_index_type(index_name)
                    
                    all_results.extend(results)
                    
                except Exception as e:
                    logger.warning(f"Search failed for index {index_name}: {e}")
                    continue
            
            # Sort by relevance score and limit results
            all_results.sort(key=lambda x: x.get("@search.score", 0), reverse=True)
            all_results = all_results[:top_k]
            
            return {
                "query": query,
                "index_type": index_type,
                "search_type": search_type,
                "total_results": len(all_results),
                "results": all_results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Search documents failed: {e}")
            return {
                "error": str(e),
                "query": query,
                "results": [],
                "total_results": 0
            }
    
    async def get_document_chunks(
        self, 
        document_id: str, 
        index_type: str = "policy"
    ) -> Dict[str, Any]:
        """
        Get all chunks for a specific document
        
        Args:
            document_id: Document identifier
            index_type: "policy" or "claims"
            
        Returns:
            Document chunks with metadata
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            index_name = self._get_index_for_type(index_type)
            if not index_name:
                return {"error": f"No index configured for type: {index_type}"}
            
            chunks = await self.azure_manager.get_chunks_for_document(index_name, document_id)
            
            return {
                "document_id": document_id,
                "index_type": index_type,
                "index_name": index_name,
                "total_chunks": len(chunks),
                "chunks": chunks,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Get document chunks failed: {e}")
            return {
                "error": str(e),
                "document_id": document_id,
                "chunks": [],
                "total_chunks": 0
            }
    
    async def get_index_metrics(self, index_type: str = "all") -> Dict[str, Any]:
        """
        Get metrics for search indexes
        
        Args:
            index_type: "policy", "claims", "financial", or "all"
            
        Returns:
            Index metrics and statistics
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            indexes = self._get_indexes_for_type(index_type)
            
            metrics = {
                "total_documents": 0,
                "total_chunks": 0,
                "indexes": {}
            }
            
            for index_name in indexes:
                try:
                    # Get documents for this index
                    documents = await self.azure_manager.list_unique_documents(index_name)
                    
                    # Estimate chunks
                    client = self.azure_manager.get_search_client_for_index(index_name)
                    search_results = await client.search(search_text="*", top=1000, query_type="simple")
                    chunk_count = 0
                    async for _ in search_results:
                        chunk_count += 1
                    
                    index_metrics = {
                        "documents": len(documents),
                        "chunks": chunk_count,
                        "index_type": self._get_index_type(index_name)
                    }
                    
                    metrics["indexes"][index_name] = index_metrics
                    metrics["total_documents"] += len(documents)
                    metrics["total_chunks"] += chunk_count
                    
                except Exception as e:
                    logger.warning(f"Failed to get metrics for index {index_name}: {e}")
                    metrics["indexes"][index_name] = {"error": str(e)}
            
            return metrics
            
        except Exception as e:
            logger.error(f"Get index metrics failed: {e}")
            return {"error": str(e)}
    
    def _get_indexes_for_type(self, index_type: str) -> List[str]:
        """Get list of index names for the specified type"""
        if index_type == "policy":
            return [settings.AZURE_SEARCH_POLICY_INDEX_NAME] if settings.AZURE_SEARCH_POLICY_INDEX_NAME else []
        elif index_type == "claims":
            return [settings.AZURE_SEARCH_CLAIMS_INDEX_NAME] if settings.AZURE_SEARCH_CLAIMS_INDEX_NAME else []
        elif index_type == "financial":
            return [settings.AZURE_SEARCH_INDEX_NAME] if settings.AZURE_SEARCH_INDEX_NAME else []
        elif index_type == "all":
            indexes = []
            if settings.AZURE_SEARCH_INDEX_NAME:
                indexes.append(settings.AZURE_SEARCH_INDEX_NAME)
            if settings.AZURE_SEARCH_POLICY_INDEX_NAME:
                indexes.append(settings.AZURE_SEARCH_POLICY_INDEX_NAME)
            if settings.AZURE_SEARCH_CLAIMS_INDEX_NAME:
                indexes.append(settings.AZURE_SEARCH_CLAIMS_INDEX_NAME)
            return indexes
        else:
            return []
    
    def _get_index_for_type(self, index_type: str) -> Optional[str]:
        """Get single index name for the specified type"""
        indexes = self._get_indexes_for_type(index_type)
        return indexes[0] if indexes else None
    
    def _get_index_type(self, index_name: str) -> str:
        """Get the type of an index based on its name"""
        if index_name == settings.AZURE_SEARCH_POLICY_INDEX_NAME:
            return "policy"
        elif index_name == settings.AZURE_SEARCH_CLAIMS_INDEX_NAME:
            return "claims"
        elif index_name == settings.AZURE_SEARCH_INDEX_NAME:
            return "financial"
        else:
            return "unknown"
    
    def get_tool_schema(self) -> Dict[str, Any]:
        """Get the tool schema for Azure AI Foundry agent configuration"""
        return {
            "name": "azure_search_tool",
            "description": "Search and retrieve documents from Azure AI Search indexes",
            "type": "azure_ai_search",
            "connection_name": self.connection_name,
            "capabilities": [
                "search_documents",
                "get_document_chunks", 
                "get_index_metrics"
            ],
            "supported_index_types": ["policy", "claims", "financial", "all"],
            "supported_search_types": ["simple", "semantic", "vector", "hybrid"]
        }
