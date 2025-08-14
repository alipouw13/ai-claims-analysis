"""
Knowledge Base Tool for Azure AI Foundry Agents

This tool provides knowledge base management functionality to agents,
allowing them to interact with the document store, manage policies and claims,
and perform knowledge base operations.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.core.config import settings
from app.services.azure_services import AzureServiceManager

logger = logging.getLogger(__name__)

class KnowledgeBaseTool:
    """
    Knowledge Base tool for Azure AI Foundry agents
    
    This tool can be attached to agents to provide:
    - Knowledge base management
    - Document operations
    - Policy and claims management
    - Knowledge base analytics
    """
    
    def __init__(self):
        self.azure_manager = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the Knowledge Base tool"""
        try:
            # Initialize Azure Service Manager
            self.azure_manager = AzureServiceManager()
            await self.azure_manager.initialize()
            
            self._initialized = True
            logger.info("Knowledge Base tool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Knowledge Base tool: {e}")
            raise
    
    async def get_knowledge_base_stats(self, index_type: str = "all") -> Dict[str, Any]:
        """
        Get knowledge base statistics
        
        Args:
            index_type: "policy", "claims", "financial", or "all"
            
        Returns:
            Knowledge base statistics
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Get indexes for the specified type
            indexes = self._get_indexes_for_type(index_type)
            
            total_documents = 0
            total_chunks = 0
            documents_by_type = {}
            
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
                    
                    index_type_label = self._get_index_type(index_name)
                    documents_by_type[index_type_label] = len(documents)
                    total_documents += len(documents)
                    total_chunks += chunk_count
                    
                except Exception as e:
                    logger.warning(f"Failed to get stats for index {index_name}: {e}")
            
            return {
                "total_documents": total_documents,
                "total_chunks": total_chunks,
                "documents_by_type": documents_by_type,
                "index_type": index_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Get knowledge base stats failed: {e}")
            return {
                "error": str(e),
                "total_documents": 0,
                "total_chunks": 0,
                "documents_by_type": {}
            }
    
    async def list_documents(
        self, 
        index_type: str = "all",
        document_type: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List documents in the knowledge base
        
        Args:
            index_type: "policy", "claims", "financial", or "all"
            document_type: Filter by document type
            limit: Number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of documents with metadata
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Get indexes for the specified type
            indexes = self._get_indexes_for_type(index_type)
            
            all_documents = []
            for index_name in indexes:
                try:
                    documents = await self.azure_manager.list_unique_documents(index_name)
                    
                    # Add index metadata
                    for doc in documents:
                        doc["index_name"] = index_name
                        doc["index_type"] = self._get_index_type(index_name)
                        doc["status"] = "completed"
                        doc.setdefault("type", "")
                        doc.setdefault("chunks", None)
                        doc.setdefault("conflicts", None)
                    
                    all_documents.extend(documents)
                    
                except Exception as e:
                    logger.warning(f"Failed to list documents for index {index_name}: {e}")
            
            # Apply filters
            if document_type:
                all_documents = [doc for doc in all_documents if doc.get("type") == document_type]
            
            # Apply pagination
            total_count = len(all_documents)
            all_documents = all_documents[offset:offset + limit]
            
            return {
                "documents": all_documents,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "index_type": index_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"List documents failed: {e}")
            return {
                "error": str(e),
                "documents": [],
                "total_count": 0
            }
    
    async def get_document_details(
        self, 
        document_id: str, 
        index_type: str = "policy"
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific document
        
        Args:
            document_id: Document identifier
            index_type: "policy" or "claims"
            
        Returns:
            Document details with chunks and metadata
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            index_name = self._get_index_for_type(index_type)
            if not index_name:
                return {"error": f"No index configured for type: {index_type}"}
            
            # Get document chunks
            chunks = await self.azure_manager.get_chunks_for_document(index_name, document_id)
            
            # Get document metadata
            documents = await self.azure_manager.list_unique_documents(index_name)
            document_info = next((doc for doc in documents if doc.get("id") == document_id), None)
            
            if not document_info:
                return {"error": f"Document {document_id} not found"}
            
            return {
                "document_id": document_id,
                "document_info": document_info,
                "index_name": index_name,
                "index_type": index_type,
                "total_chunks": len(chunks),
                "chunks": chunks,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Get document details failed: {e}")
            return {
                "error": str(e),
                "document_id": document_id,
                "chunks": [],
                "total_chunks": 0
            }
    
    async def search_knowledge_base(
        self, 
        query: str, 
        index_type: str = "all",
        top_k: int = 10,
        filters: str = None
    ) -> Dict[str, Any]:
        """
        Search the knowledge base
        
        Args:
            query: Search query
            index_type: "policy", "claims", "financial", or "all"
            top_k: Number of results to return
            filters: OData filter expression
            
        Returns:
            Search results with documents and relevance scores
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Get indexes for the specified type
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
                "total_results": len(all_results),
                "results": all_results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Search knowledge base failed: {e}")
            return {
                "error": str(e),
                "query": query,
                "results": [],
                "total_results": 0
            }
    
    async def get_knowledge_base_health(self) -> Dict[str, Any]:
        """
        Get knowledge base health status
        
        Returns:
            Health status of all indexes and services
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            health_status = {
                "overall_status": "healthy",
                "indexes": {},
                "services": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Check all indexes
            all_indexes = self._get_indexes_for_type("all")
            
            for index_name in all_indexes:
                try:
                    # Test search on this index
                    client = self.azure_manager.get_search_client_for_index(index_name)
                    search_results = await client.search(search_text="*", top=1, query_type="simple")
                    
                    # Count results to verify index is accessible
                    count = 0
                    async for _ in search_results:
                        count += 1
                    
                    health_status["indexes"][index_name] = {
                        "status": "healthy",
                        "accessible": True,
                        "document_count": count
                    }
                    
                except Exception as e:
                    health_status["indexes"][index_name] = {
                        "status": "unhealthy",
                        "accessible": False,
                        "error": str(e)
                    }
                    health_status["overall_status"] = "degraded"
            
            # Check Azure services
            try:
                # Test Azure Search service
                test_search = await self.azure_manager.hybrid_search("*", top_k=1)
                health_status["services"]["azure_search"] = {
                    "status": "healthy",
                    "accessible": True
                }
            except Exception as e:
                health_status["services"]["azure_search"] = {
                    "status": "unhealthy",
                    "accessible": False,
                    "error": str(e)
                }
                health_status["overall_status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Get knowledge base health failed: {e}")
            return {
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
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
            "name": "knowledge_base_tool",
            "description": "Manage and query the knowledge base with policies and claims",
            "type": "knowledge_base",
            "capabilities": [
                "get_knowledge_base_stats",
                "list_documents",
                "get_document_details",
                "search_knowledge_base",
                "get_knowledge_base_health"
            ],
            "supported_index_types": ["policy", "claims", "financial", "all"],
            "supported_operations": ["read", "search", "analytics"]
        }
