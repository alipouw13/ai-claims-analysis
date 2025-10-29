from azure.search.documents import SearchClient
from azure.search.documents.aio import SearchClient as AsyncSearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from openai import AzureOpenAI, AsyncAzureOpenAI
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
import asyncio
import logging
import os
import platform
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
import hashlib
import json
from dataclasses import dataclass
import time
import httpx

# Configure Windows event loop policy for Azure SDK compatibility
if platform.system() == "Windows":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from app.core.config import settings
from app.core import observability
from app.services.azure_storage_manager import AzureStorageManager, MockStorageManager
from app.services.azure_openai_deployment_service import AzureOpenAIDeploymentService, MockAzureOpenAIDeploymentService

logger = logging.getLogger(__name__)

class MockSearchClient:
    def __init__(self):
        self.documents = []
    
    def upload_documents(self, documents):
        self.documents.extend(documents)
        return {"status": "success", "count": len(documents)}
    
    def search(self, search_text=None, vector_queries=None, **kwargs):
        return [
            {
                "id": "mock-doc-1",
                "content": "Sample financial content from 10-K report",
                "title": "Sample Financial Corporation 10-K",
                "document_type": "10-K",
                "company": "Sample Financial Corporation",
                "filing_date": "2023-12-31",
                "source_url": "mock://sample-10k.pdf",
                "credibility_score": 0.95
            }
        ]

class MockSearchIndexClient:
    def create_or_update_index(self, index):
        return {"status": "success", "name": index.name}

class MockDocumentAnalysisClient:
    def begin_analyze_document(self, model_id, document):
        class MockPoller:
            def result(self):
                class MockResult:
                    def __init__(self):
                        self.content = "Mock extracted content from financial document"
                        self.pages = [{"page_number": 1}]
                        self.tables = []
                        self.key_value_pairs = []
                return MockResult()
        return MockPoller()

class MockCosmosClient:
    def __init__(self):
        self.sessions = {}
    
    def get_database_client(self, database_name):
        return MockDatabaseClient(self.sessions)
    
    def close(self):
        pass

class MockDatabaseClient:
    def __init__(self, sessions):
        self.sessions = sessions
    
    def get_container_client(self, container_name):
        return MockContainerClient(self.sessions)

class MockContainerClient:
    def __init__(self, sessions):
        self.sessions = sessions
    
    def read_item(self, item, partition_key):
        if item in self.sessions:
            return self.sessions[item]
        raise Exception("Item not found")
    
    def upsert_item(self, item):
        self.sessions[item["id"]] = item
        return item

class MockOpenAIClient:
    def __init__(self):
        self.embeddings = MockEmbeddings()

class MockAIFoundryClient:
    def __init__(self):
        self.agents = MockAgents()
        self.evaluations = MockEvaluations()
        self.connections = MockConnections()
    
    def get_connection_by_name(self, name: str):
        return {"name": name, "type": "mock", "status": "connected"}

class MockAgent:
    def __init__(self, agent_id: str, name: str, status: str = "active"):
        self.id = agent_id
        self.name = name
        self.status = status

class MockThread:
    def __init__(self, thread_id: str):
        self.id = thread_id

class MockRun:
    def __init__(self, run_id: str, status: str = "completed"):
        self.id = run_id
        self.status = status

class MockMessage:
    def __init__(self, message_id: str, content: str, role: str = "assistant"):
        self.id = message_id
        self.role = role
        self.content = [{"text": {"value": content}}]

class MockAgents:
    def create_agent(self, **kwargs):
        return MockAgent("mock-agent-1", kwargs.get("name", "Mock Agent"))
    
    def create_thread(self):
        return MockThread("mock-thread-1")
    
    def create_message(self, thread_id: str, **kwargs):
        return MockMessage("mock-message-1", kwargs.get("content", "Mock message content"))
    
    def create_run(self, thread_id: str, **kwargs):
        return MockRun("mock-run-1")
    
    def get_run(self, thread_id: str, run_id: str):
        return MockRun(run_id, "completed")
    
    def list_messages(self, thread_id: str, **kwargs):
        class MockMessageList:
            def __init__(self):
                self.data = [MockMessage("mock-message-1", "Mock response from financial AI agent")]
        return MockMessageList()
    
    def list_agents(self):
        return [MockAgent("mock-agent-1", "Mock Agent")]

class MockEvaluations:
    def create_evaluation(self, **kwargs):
        return {"id": "mock-eval-1", "status": "completed", "score": 0.85}
    
    def get_evaluation(self, evaluation_id: str):
        return {"id": evaluation_id, "status": "completed", "score": 0.85}

class MockConnections:
    def list_connections(self):
        return [{"name": "mock-connection", "type": "azure_openai", "status": "connected"}]
    
    def list(self):
        return [
            {
                "name": "mock-azure-openai-connection",
                "type": "azure_openai", 
                "status": "connected",
                "endpoint": "https://mock-openai.openai.azure.com/",
                "resource_id": "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.CognitiveServices/accounts/mock-openai"
            }
        ]

class MockEmbeddings:
    def create(self, input, model):
        class MockResponse:
            def __init__(self):
                self.data = [MockEmbeddingData()]
        return MockResponse()

class MockEmbeddingData:
    def __init__(self):
        import random
        self.embedding = [random.random() for _ in range(1536)]

class AzureServiceManager:
    def __init__(self):
        self.search_client = None
        self.search_index_client = None
        self.form_recognizer_client = None
        self.cosmos_client = None
        self.openai_client = None
        self.ai_foundry_client = None
        self.project_client = None
        self.credential = None
        self.storage_manager = None
        
        # Cache for expensive operations
        self._models_cache = None
        self._models_cache_time = None
        self._cache_ttl = 300  # 5 minutes
        
    async def initialize(self):
        """Initialize all Azure services"""
        try:
            # Force real Azure services - don't use mock services
            logger.info("Initializing real Azure services...")
            
            if settings.AZURE_CLIENT_SECRET and settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID:
                self.credential = ClientSecretCredential(
                    tenant_id=settings.AZURE_TENANT_ID,
                    client_id=settings.AZURE_CLIENT_ID,
                    client_secret=settings.AZURE_CLIENT_SECRET
                )
                logger.info("Using Service Principal (SPN) authentication")
            else:
                raise ValueError("SPN authentication required: AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET must be provided")
            
            search_endpoint = f"https://{settings.AZURE_SEARCH_SERVICE_NAME}.search.windows.net"
            
            # Use API key authentication if available, otherwise use Service Principal
            if settings.AZURE_SEARCH_API_KEY:
                from azure.core.credentials import AzureKeyCredential
                search_credential = AzureKeyCredential(settings.AZURE_SEARCH_API_KEY)
                logger.info("Using API key authentication for Azure Search")
            else:
                search_credential = self.credential
                logger.info("Using Service Principal authentication for Azure Search")
            
            self.search_client = AsyncSearchClient(
                endpoint=search_endpoint,
                index_name=settings.AZURE_SEARCH_INDEX_NAME,
                credential=search_credential
            )
            # Store endpoint/credential to create scoped clients for other indexes
            self._search_endpoint = search_endpoint
            self._search_credential = search_credential
            
            self.search_index_client = SearchIndexClient(
                endpoint=search_endpoint,
                credential=search_credential
            )
            
            self.cosmos_client = CosmosClient(
                url=settings.AZURE_COSMOS_ENDPOINT,
                credential=self.credential
            )
            
            # Initialize Document Intelligence client (optional)
            if hasattr(settings, 'AZURE_FORM_RECOGNIZER_ENDPOINT') and settings.AZURE_FORM_RECOGNIZER_ENDPOINT:
                self.form_recognizer_client = DocumentAnalysisClient(
                    endpoint=settings.AZURE_FORM_RECOGNIZER_ENDPOINT,
                    credential=self.credential
                )
                logger.info("Document Intelligence client initialized")
            else:
                self.form_recognizer_client = None
                logger.warning("Document Intelligence endpoint not configured - document processing will use fallback methods")
            
            # Initialize Azure AI Foundry (prefer endpoint+credential per latest SDK; fall back if needed)
            self.project_client = None
            self.ai_foundry_client = None
            try:
                from importlib.metadata import version, PackageNotFoundError
            except Exception:
                version = None  # Best effort only
            try:
                # Gather inputs
                endpoint = getattr(settings, 'AZURE_AI_PROJECT_ENDPOINT', None)
                conn_str = getattr(settings, 'AZURE_AI_PROJECT_CONNECTION_STRING', None)
                subscription_id = getattr(settings, 'AZURE_SUBSCRIPTION_ID', None)
                resource_group = getattr(settings, 'AZURE_AI_FOUNDRY_RESOURCE_GROUP', None) or os.getenv('AZURE_AI_PROJECT_RESOURCE_GROUP')
                project_name = getattr(settings, 'AZURE_AI_PROJECT_NAME', None) or os.getenv('AZURE_AI_FOUNDRY_PROJECT_NAME')

                # Try modern endpoint-only signature first (per docs). This is what the
                # alipouw13/agenticrag sample uses as well.
                if endpoint:
                    try:
                        # Prefer endpoint-only signature introduced in azure-ai-projects >= 1.0.0
                        # Using DefaultAzureCredential here because many environments rely on az cli / managed identity.
                        self.project_client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
                        self.ai_foundry_client = self.project_client
                        logger.info("Azure AI Foundry project client initialized via endpoint-only signature")
                    except TypeError as te:
                        # Library may be older and require the legacy signature; fall back below
                        logger.info(f"Endpoint-only init not supported by installed azure-ai-projects: {te}")
                        self.project_client = None
                        self.ai_foundry_client = None
                    except Exception as e:
                        # If endpoint-only call fails for reasons other than signature, report and continue to fallback
                        logger.error(f"Endpoint-only AIProjectClient init failed: {e}")
                        self.project_client = None
                        self.ai_foundry_client = None

                # If still not initialized, parse connection string or use discrete vars for legacy signature
                if self.project_client is None:
                    if conn_str and not (subscription_id and resource_group and project_name):
                        try:
                            parts = [p for p in conn_str.replace('\n',';').split(';') if p]
                            kv = {}
                            raw = []
                            for p in parts:
                                if '=' in p:
                                    k, v = p.split('=', 1)
                                    kv[k.strip().lower()] = v.strip()
                                else:
                                    raw.append(p.strip())
                            subscription_id = subscription_id or kv.get('subscriptionid') or kv.get('azuresubscriptionid') or (raw[0] if len(raw) > 0 else None)
                            resource_group = resource_group or kv.get('resourcegroup') or kv.get('resourcegroupname') or (raw[1] if len(raw) > 1 else None)
                            project_name = project_name or kv.get('projectname') or kv.get('project') or (raw[2] if len(raw) > 2 else None)
                            endpoint = endpoint or kv.get('hostname') or kv.get('endpoint') or next((t for t in raw if t.startswith('http')), None)
                        except Exception as parse_err:
                            logger.warning(f"Could not parse AZURE_AI_PROJECT_CONNECTION_STRING: {parse_err}")

                    if subscription_id and resource_group and project_name:
                        kwargs = {
                            'credential': DefaultAzureCredential(),
                            'subscription_id': subscription_id,
                            'resource_group_name': resource_group,
                            'project_name': project_name,
                        }
                        if endpoint:
                            kwargs['endpoint'] = endpoint
                        self.project_client = AIProjectClient(**kwargs)
                        self.ai_foundry_client = self.project_client
                        logger.info("Azure AI Foundry project client initialized via legacy signature")

                if self.project_client is None:
                    if endpoint:
                        logger.error("AI Foundry endpoint detected but client could not be initialized. Ensure azure-ai-projects >= 1.0.0 (pip install -U azure-ai-projects) and that this is a Foundry Project endpoint (not Cognitive Services). Docs: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview?pivots=programming-language-python")
                    else:
                        logger.info("Azure AI Foundry configuration not found; skipping initialization")
            except Exception as e:
                logger.error(f"Failed to initialize Azure AI Foundry client: {e}")
                self.project_client = None
                self.ai_foundry_client = None
            
            self.openai_client = AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION
            )
            
            # Ensure search index exists
            await self.ensure_search_index_exists()
            
            # Initialize Azure Storage Manager - commented out due to Windows event loop issue
            # self.storage_manager = AzureStorageManager()
            # await self.storage_manager.initialize()
            # logger.info("Azure Storage Manager initialized")
            
            logger.info("Azure services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure services: {e}")
            raise
    
    async def _initialize_mock_services(self):
        """Initialize mock services for local development"""
        self.search_client = MockSearchClient()
        self.search_index_client = MockSearchIndexClient()
        self.form_recognizer_client = MockDocumentAnalysisClient()
        self.cosmos_client = MockCosmosClient()
        self.openai_client = MockOpenAIClient()
        self.ai_foundry_client = MockAIFoundryClient()
        self.project_client = MockAIFoundryClient()  # Same mock for project client
        self.credential = None
        
        self.storage_manager = MockStorageManager()
        await self.storage_manager.initialize()
        
        logger.info("Mock Azure services initialized for local development")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Close all Azure clients that may have internal HTTP sessions
            if hasattr(self, 'cosmos_client') and self.cosmos_client:
                if hasattr(self.cosmos_client, 'close'):
                    self.cosmos_client.close()
                    
            if hasattr(self, 'project_client') and self.project_client:
                if hasattr(self.project_client, 'close'):
                    await self.project_client.close()
                elif hasattr(self.project_client, '_client') and hasattr(self.project_client._client, 'close'):
                    await self.project_client._client.close()
                    
            if hasattr(self, 'ai_foundry_client') and self.ai_foundry_client:
                if hasattr(self.ai_foundry_client, 'close'):
                    await self.ai_foundry_client.close()
                elif hasattr(self.ai_foundry_client, '_client') and hasattr(self.ai_foundry_client._client, 'close'):
                    await self.ai_foundry_client._client.close()
                    
            if hasattr(self, 'openai_client') and self.openai_client:
                if hasattr(self.openai_client, 'close'):
                    await self.openai_client.close()
                    
            if hasattr(self, 'storage_manager') and self.storage_manager:
                if hasattr(self.storage_manager, 'cleanup'):
                    await self.storage_manager.cleanup()
                    
            logger.info("Azure services cleaned up")
        except Exception as e:
            logger.error(f"Error during Azure services cleanup: {e}")
    
    def _validate_azure_credentials(self) -> bool:
        """Validate that all required Azure credentials are present"""
        required_settings = [
            'AZURE_CLIENT_SECRET',
            'AZURE_TENANT_ID', 
            'AZURE_CLIENT_ID',
            'AZURE_SEARCH_SERVICE_NAME',
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_COSMOS_ENDPOINT'        ]
        
        missing_settings = []
        for setting in required_settings:
            if not getattr(settings, setting, None):
                missing_settings.append(setting)
        
        if missing_settings:
            logger.warning(f"Missing Azure credentials: {', '.join(missing_settings)}")
            return False
            
        return True
    
    def get_project_client(self) -> Optional[AIProjectClient]:
        """Get the Azure AI Foundry project client for agent services"""
        return self.project_client
    
    async def create_search_index(self):
        """
        DEPRECATED: Use ensure_search_index_exists() instead.
        This method is kept for backward compatibility but will call ensure_search_index_exists().
        """
        logger.warning("create_search_index() is deprecated. Use ensure_search_index_exists() instead.")
        return await self.ensure_search_index_exists()

    async def ensure_search_index_exists(self) -> bool:
        """Ensure the search index exists, create it if it doesn't"""
        try:
            logger.info(f"Checking if search index '{settings.AZURE_SEARCH_INDEX_NAME}' exists")
            
            # Check if index exists
            try:
                index = self.search_index_client.get_index(settings.AZURE_SEARCH_INDEX_NAME)
                logger.info(f"Search index '{settings.AZURE_SEARCH_INDEX_NAME}' already exists with {len(index.fields)} fields")
                return True
            except Exception as e:
                logger.info(f"Search index '{settings.AZURE_SEARCH_INDEX_NAME}' does not exist, creating it. Error: {e}")
                
            # Create the index
            from azure.search.documents.indexes.models import (
                SearchIndex, SearchField, SearchFieldDataType, SimpleField, 
                SearchableField, VectorSearch, HnswAlgorithmConfiguration,
                VectorSearchProfile, SemanticConfiguration, SemanticPrioritizedFields,
                SemanticField, SemanticSearch
            )
            fields = [
                SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="parent_id", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="chunk", type=SearchFieldDataType.String),
                SearchableField(name="title", type=SearchFieldDataType.String),
                SearchField(
                    name="content_vector", 
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_profile_name="default-vector-profile"
                )
            ]
            
            # Configure vector search
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="default-hnsw",
                        parameters={
                            "m": 4,
                            "efConstruction": 400,
                            "efSearch": 500,
                            "metric": "cosine"
                        }
                    )
                ],
                profiles=[
                    VectorSearchProfile(
                        name="default-vector-profile",
                        algorithm_configuration_name="default-hnsw"
                    )
                ]
            )
              # Configure semantic search with SEC-specific fields
            semantic_config = SemanticConfiguration(
                name="default-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[
                        SemanticField(field_name="chunk")
                    ],
                    keywords_fields=[
                        SemanticField(field_name="title")
                    ]
                )
            )
            
            semantic_search = SemanticSearch(
                configurations=[semantic_config],
                default_configuration_name="default-semantic-config"
            )
              # Create the index
            index = SearchIndex(
                name=settings.AZURE_SEARCH_INDEX_NAME,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )
            result = self.search_index_client.create_index(index)
            logger.info(f"Successfully created search index '{settings.AZURE_SEARCH_INDEX_NAME}'")
            
            # Also ensure policy and claims indexes exist if configured and distinct
            try:
                policy_ix = getattr(settings, 'AZURE_SEARCH_POLICY_INDEX_NAME', None)
                claims_ix = getattr(settings, 'AZURE_SEARCH_CLAIMS_INDEX_NAME', None)
                for ix_name in {policy_ix, claims_ix}:
                    if not ix_name or ix_name == settings.AZURE_SEARCH_INDEX_NAME:
                        continue
                    try:
                        self.search_index_client.get_index(ix_name)
                        logger.info(f"Index '{ix_name}' already exists")
                    except Exception:
                        logger.info(f"Creating additional index '{ix_name}' for policy/claims separation")
                        # Use Content Processing Solution Accelerator schema for all indexes
                        if ix_name == policy_ix:
                            policy_fields = [
                                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                                SimpleField(name="parent_id", type=SearchFieldDataType.String, filterable=True),
                                SearchableField(name="content", type=SearchFieldDataType.String),
                                SearchableField(name="title", type=SearchFieldDataType.String),
                                SearchableField(name="source", type=SearchFieldDataType.String),
                                SearchField(
                                    name="content_vector", 
                                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                                    searchable=True,
                                    vector_search_dimensions=1536,
                                    vector_search_profile_name="default-vector-profile"
                                )
                            ]
                            addl_index = SearchIndex(
                                name=ix_name,
                                fields=policy_fields,
                                vector_search=vector_search,
                                semantic_search=semantic_search
                            )
                        elif ix_name == claims_ix:
                            claims_fields = [
                                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                                SimpleField(name="parent_id", type=SearchFieldDataType.String, filterable=True),
                                SearchableField(name="content", type=SearchFieldDataType.String),
                                SearchableField(name="title", type=SearchFieldDataType.String),
                                SearchableField(name="source", type=SearchFieldDataType.String),
                                SearchField(
                                    name="content_vector", 
                                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                                    searchable=True,
                                    vector_search_dimensions=1536,
                                    vector_search_profile_name="default-vector-profile"
                                )
                            ]
                            addl_index = SearchIndex(
                                name=ix_name,
                                fields=claims_fields,
                                vector_search=vector_search,
                                semantic_search=semantic_search
                            )
                        else:
                            # Fallback to generic schema
                            addl_index = SearchIndex(
                            name=ix_name,
                            fields=fields,
                            vector_search=vector_search,
                            semantic_search=semantic_search
                        )
                        self.search_index_client.create_index(addl_index)
                        logger.info(f"Successfully created index '{ix_name}'")
            except Exception as extra_err:
                logger.warning(f"Failed to ensure policy/claims indexes: {extra_err}")
            return True
        except Exception as e:
            logger.error(f"Failed to ensure search index exists: {e}")
            return False

    async def get_embedding(self, text: str, model: str = None, token_tracker=None, tracking_id: str = None) -> List[float]:
        """Get embedding for text using Azure OpenAI async client"""
        try:
            # Use deployment name from settings
            # For Azure OpenAI, we use the deployment name as the model parameter
            deployment_name = model or settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
            
            # Add timing and thread logging for debugging
            import threading
            import time
            thread_id = threading.get_ident()
            start_time = time.time()
            logger.debug(f"🔤 [Thread-{thread_id}] Starting embedding request for {len(text)} chars using {deployment_name}")
            
            # Use async client directly - no need for run_in_executor
            response = await self.openai_client.embeddings.create(
                input=text,
                model=deployment_name
            )
            
            elapsed_time = time.time() - start_time
            logger.debug(f"✅ [Thread-{thread_id}] Embedding completed in {elapsed_time:.2f}s")
            
            # Track token usage for embedding if tracker is provided
            if token_tracker and tracking_id and hasattr(response, 'usage'):
                try:
                    await token_tracker.update_usage(
                        tracking_id=tracking_id,
                        model_name=deployment_name,
                        deployment_name=deployment_name,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=0,  # Embeddings don't have completion tokens
                        total_tokens=response.usage.total_tokens,
                        input_text=text[:200] + "..." if len(text) > 200 else text,
                        output_text=f"Generated embedding vector of dimension {len(response.data[0].embedding)}"
                    )
                    logger.info(f"Embedding token usage tracked: {response.usage.total_tokens} tokens")
                except Exception as tracking_error:
                    logger.error(f"Failed to track embedding token usage: {tracking_error}")
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            raise

    async def hybrid_search(self, query: str, top_k: int = 10, filters: str = None, min_score: float = 0.0, token_tracker=None, tracking_id: str = None) -> List[Dict]:
        """Perform hybrid search (vector + keyword) on the knowledge base"""
        try:
            logger.info(f"🔍 Hybrid search with token tracking: tracker={token_tracker is not None}, tracking_id={tracking_id}")
            # Add timing and thread logging for debugging
            import threading
            thread_id = threading.get_ident()
            start_time = time.time()
            logger.debug(f"🔍 [Thread-{thread_id}] Starting hybrid search for query: '{query[:50]}...' (top_k={top_k})")
            
            query_vector = await self.get_embedding(query, token_tracker=token_tracker, tracking_id=tracking_id)
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=top_k,
                fields="content_vector"
            )
            
            async def _search_with_client(client: AsyncSearchClient) -> List[Dict]:
                search_start_local = time.time()

                async def _run(select_fields: bool) -> List[Dict]:
                    try:
                        # Choose semantic vs simple per index
                        index_name = getattr(client, "_index_name", "")
                        is_sec = index_name == getattr(settings, 'AZURE_SEARCH_INDEX_NAME', index_name)

                        if is_sec:
                            kwargs = dict(
                                search_text=query,
                                vector_queries=[vector_query],
                                filter=filters,
                                top=top_k,
                                query_type="semantic",
                                semantic_configuration_name="default-semantic-config",
                            )
                        else:
                            kwargs = dict(
                                search_text=query,
                                filter=filters,
                                top=top_k,
                                query_type="simple",
                            )
                        if select_fields:
                            kwargs["select"] = [
                                "id", "content", "title", "document_id", "source", "chunk_id",
                                "document_type", "company", "filing_date", "section_type",
                                "page_number", "credibility_score", "processed_at", "citation_info",
                                "ticker", "cik", "form_type", "accession_number", "industry",
                                "document_url", "sic", "entity_type", "period_end_date",
                                "chunk_index", "content_type", "chunk_method", "file_size",
                            ]
                        results_local = await client.search(**kwargs)
                        filtered: List[Dict] = []
                        async for r in results_local:
                            rdict = dict(r)
                            score = getattr(r, '@search.score', 0.0)
                            if score >= min_score:
                                rdict['search_score'] = score
                                filtered.append(rdict)
                        return filtered
                    except Exception as e:
                        if select_fields:
                            logger.warning(f"Hybrid search failed with select, retrying without select: {e}")
                            try:
                                return await _run(False)
                            except Exception as inner:
                                logger.warning(f"Retry without select also failed: {inner}. Falling back to simple search (no vector)")
                                simple_results = await client.search(search_text=query, filter=filters, top=top_k, query_type="simple")
                                out: List[Dict] = []
                                async for r in simple_results:
                                    rd = dict(r)
                                    rd['search_score'] = getattr(r, '@search.score', 0.0)
                                    out.append(rd)
                                return out
                        raise

                filtered = await _run(True)
                _ = time.time() - search_start_local
                return filtered

            # If configured, search both policy and claims indexes in parallel and merge
            search_tasks: List = []
            if getattr(settings, 'AZURE_SEARCH_QUERY_BOTH_INDEXES', False):
                index_names = list({
                    settings.AZURE_SEARCH_POLICY_INDEX_NAME or settings.AZURE_SEARCH_INDEX_NAME,
                    settings.AZURE_SEARCH_CLAIMS_INDEX_NAME or settings.AZURE_SEARCH_INDEX_NAME,
                })
                clients = [self.get_search_client_for_index(ix) for ix in index_names if ix]
                for c in clients:
                    search_tasks.append(_search_with_client(c))
                merged_lists = await asyncio.gather(*search_tasks)
                filtered_results = [item for sub in merged_lists for item in sub]
                # Deduplicate by a stable key; fall back if 'id' missing
                best_by_id: Dict[str, Dict] = {}
                try:
                    import uuid as _uuid
                except Exception:
                    _uuid = None
                for item in filtered_results:
                    doc_key = (
                        item.get('id') or
                        item.get('document_id') or
                        item.get('chunk_id') or
                        item.get('parent_id') or
                        (f"auto_{_uuid.uuid4()}" if _uuid else str(len(best_by_id)+1))
                    )
                    if doc_key not in best_by_id or item.get('search_score', 0) > best_by_id[doc_key].get('search_score', 0):
                        best_by_id[doc_key] = item
                filtered_results = sorted(best_by_id.values(), key=lambda x: x.get('search_score', 0), reverse=True)[:top_k]
            else:
                filtered_results = await _search_with_client(self.search_client)
            
            elapsed_time = time.time() - start_time
            logger.debug(f"✅ [Thread-{thread_id}] Hybrid search completed in {elapsed_time:.2f}s, found: {len(filtered_results)} results")
            
            return filtered_results
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise    
            
    async def add_documents_to_index(self, documents: List[Dict]) -> bool:
        """Add or update documents in the search index"""
        try:
            logger.info(f"Starting add_documents_to_index with {len(documents)} documents")
            
            # with observability.trace_operation("azure_add_documents_to_index") as span:
            #     span.set_attribute("documents_count", len(documents))
            
            validated_documents = []
            for doc in documents:
                if self._validate_document_schema(doc):
                    validated_documents.append(doc)
                else:
                    logger.warning(f"Skipping invalid document: {doc.get('id', 'unknown')}")
                    
            if not validated_documents:
                logger.error("No valid documents to upload after validation")
                return False
                
            logger.info(f"Validated {len(validated_documents)} documents, uploading to search index")
            result = await self.search_client.upload_documents(validated_documents)
            logger.info(f"Search client upload_documents result: {result}")
            
            #     span.set_attribute("uploaded_count", len(validated_documents))
            #     span.set_attribute("success", True)
            logger.info(f"Successfully uploaded {len(validated_documents)} documents to search index")
            # observability.track_kb_update("search_index", len(validated_documents), 0)  # Method not available
            
            return True
                
        except Exception as e:
            logger.error(f"Failed to add documents to index: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
            observability.record_error("azure_add_documents_error", str(e))
            return False
    
    def _validate_document_schema(self, document: Dict) -> bool:
        """Validate document schema before uploading to search index.
        Supports both Content Processing Solution Accelerator schema (chunk_id/chunk) and 
        standard schema (id/content) for policy/claims indexes.
        """
        # Check for required fields - support both schemas
        has_chunk_schema = bool(document.get('chunk_id')) and bool(document.get('chunk'))
        has_standard_schema = bool(document.get('id')) and bool(document.get('content'))
        
        if not (has_chunk_schema or has_standard_schema):
            logger.warning("Document missing required fields: expected ('chunk_id' and 'chunk') or ('id' and 'content')")
            return False
        
        # Size limits - check the appropriate content field
        content_length = len(document.get('chunk', '') or document.get('content', '') or '')
        if content_length > 1_000_000:  # 1MB limit
            logger.warning(f"Document content too large: {content_length} characters")
            return False
            
        return True

    # --- Multi-index helpers ---
    def get_search_client_for_index(self, index_name: str) -> AsyncSearchClient:
        return AsyncSearchClient(
            endpoint=self._search_endpoint,
            index_name=index_name,
            credential=self._search_credential,
        )

    async def add_documents_to_index_name(self, index_name: str, documents: List[Dict]) -> bool:
        try:
            client = self.get_search_client_for_index(index_name)
            validated_documents = []
            for doc in documents:
                if self._validate_document_schema(doc):
                    validated_documents.append(doc)
            if not validated_documents:
                return False
            await client.upload_documents(validated_documents)
            return True
        except Exception as e:
            logger.error(f"Failed to add documents to index '{index_name}': {e}")
            return False

    async def list_unique_documents(self, index_name: str, top_k: int = 200) -> List[Dict]:
        """Return a lightweight list of unique documents from a given index.
        Groups by document_id; picks earliest chunk as representative.
        """
        try:
            client = self.get_search_client_for_index(index_name)
            # Detect vector schema (policy/claims) vs generic/SEC
            policy_ix = getattr(settings, 'AZURE_SEARCH_POLICY_INDEX_NAME', None)
            claims_ix = getattr(settings, 'AZURE_SEARCH_CLAIMS_INDEX_NAME', None)
            is_vector_schema = index_name in {policy_ix, claims_ix}
            logger.info(f"list_unique_documents: index_name={index_name}, policy_ix={policy_ix}, claims_ix={claims_ix}, is_vector_schema={is_vector_schema}")

            if is_vector_schema:
                select_fields = ["chunk_id", "parent_id", "title", "source", "processed_at"]
            else:
                select_fields = ["id", "document_id", "source", "processed_at", "file_size", "title"]
            try:
                results = await client.search(
                    search_text="*",
                    select=select_fields,
                    top=top_k,
                )
            except Exception as sel_err:
                logger.warning(f"list_unique_documents select failed for '{index_name}', retrying without select: {sel_err}")
                results = await client.search(
                    search_text="*",
                    top=top_k,
                )
            docs_by_id: Dict[str, Dict] = {}
            async for r in results:
                rd = dict(r)
                # Use parent_id for vector schema; fallback to document_id/id
                doc_id = rd.get("parent_id") if is_vector_schema else rd.get("document_id")
                if not doc_id:
                    doc_id = rd.get("id") or rd.get("chunk_id")
                if not doc_id:
                    continue
                if doc_id not in docs_by_id:
                    docs_by_id[doc_id] = {
                        "id": doc_id,
                        "filename": rd.get("title") or rd.get("source") or doc_id,
                        "uploadDate": rd.get("processed_at"),
                        "size": rd.get("file_size") or 0,
                        "chunks": 0,  # Will be counted below
                    }
                # Count chunks for this document
                docs_by_id[doc_id]["chunks"] = docs_by_id[doc_id].get("chunks", 0) + 1
            return list(docs_by_id.values())
        except Exception as e:
            logger.error(f"Failed to list documents from index '{index_name}': {e}")
            return []

    async def get_chunks_for_document(self, index_name: str, document_id: str, top_k: int = 1000) -> List[Dict]:
        """Return all chunks for a given document_id from the specified index."""
        try:
            client = self.get_search_client_for_index(index_name)
            policy_ix = getattr(settings, 'AZURE_SEARCH_POLICY_INDEX_NAME', None)
            claims_ix = getattr(settings, 'AZURE_SEARCH_CLAIMS_INDEX_NAME', None)
            is_vector_schema = index_name in {policy_ix, claims_ix}

            if is_vector_schema:
                filter_expr = f"parent_id eq '{document_id}'"
                select_fields = ["chunk_id", "parent_id", "chunk", "title"]
            else:
                filter_expr = f"document_id eq '{document_id}'"
                select_fields = ["id", "content", "metadata", "chunk_id", "section_type", "chunk_index", "source", "processed_at"]

            try:
                results = await client.search(
                    search_text="*",
                    select=select_fields,
                    filter=filter_expr,
                    top=top_k,
                )
            except Exception as sel_err:
                logger.warning(f"get_chunks_for_document select failed for '{index_name}', retrying without select: {sel_err}")
                results = await client.search(
                    search_text="*",
                    filter=filter_expr,
                    top=top_k,
                )
            chunks: List[Dict] = []
            async for r in results:
                rd = dict(r)
                if is_vector_schema:
                    # Normalize to include 'content' for UI compatibility
                    normalized = {
                        **rd,
                        "id": rd.get("chunk_id") or rd.get("id"),
                        "content": rd.get("chunk") or rd.get("content") or "",
                    }
                    chunks.append(normalized)
                else:
                    chunks.append(rd)
            return chunks
        except Exception as e:
            logger.error(f"Failed to get chunks for document '{document_id}' from index '{index_name}': {e}")
            return []
        
    async def analyze_document(self, document_content: bytes, content_type: str, filename: str = None) -> Dict:
        """Analyze document using Azure Document Intelligence with enhanced financial document processing"""
        try:
            # with observability.trace_operation("azure_analyze_document") as span:
            #     span.set_attribute("content_type", content_type)
            #     span.set_attribute("content_size", len(document_content))
            #     span.set_attribute("filename", filename or "unknown")
            
            model_id = self._select_document_model(content_type, filename)
            #     span.set_attribute("model_id", model_id)
            
            logger.info(f"Analyzing document with model {model_id}, size: {len(document_content)} bytes")
            
            poller = self.form_recognizer_client.begin_analyze_document(
                model_id=model_id,
                document=document_content
            )
            result = poller.result()
            
            extracted_content = {
                "content": result.content,
                "tables": [],
                "key_value_pairs": {},
                "pages": len(result.pages) if result.pages else 0,
                "financial_sections": [],
                "metadata": {
                    "model_used": model_id,
                    "confidence_scores": {},
                    "processing_time": None
                }
            }
            
            if result.tables:
                for i, table in enumerate(result.tables):
                    table_data = {
                        "table_id": i,
                        "cells": [],
                        "financial_context": self._identify_financial_table_context(table)
                    }
                    
                    for cell in table.cells:
                        table_data["cells"].append({
                            "content": cell.content,
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "confidence": getattr(cell, 'confidence', 0.0)
                        })
                    
                    extracted_content["tables"].append(table_data)
            
            if result.key_value_pairs:
                for kv_pair in result.key_value_pairs:
                    if kv_pair.key and kv_pair.value:
                        key_content = kv_pair.key.content
                        value_content = kv_pair.value.content
                        
                        extracted_content["key_value_pairs"][key_content] = {
                            "value": value_content,
                            "confidence": getattr(kv_pair, 'confidence', 0.0),
                            "financial_relevance": self._score_financial_relevance(key_content, value_content)
                        }
            
            extracted_content["financial_sections"] = self._identify_financial_sections(result.content, filename)
            
            #     span.set_attribute("pages_processed", extracted_content["pages"])
            #     span.set_attribute("tables_found", len(extracted_content["tables"]))
            #     span.set_attribute("kv_pairs_found", len(extracted_content["key_value_pairs"]))
            #     span.set_attribute("success", True)
            
            logger.info(f"Document analysis completed: {extracted_content['pages']} pages, {len(extracted_content['tables'])} tables")
            
            return extracted_content
                
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            observability.record_error("azure_document_analysis_error", str(e))
            raise
    
    def _select_document_model(self, content_type: str, filename: str = None) -> str:
        """Select appropriate Document Intelligence model based on content type and filename"""
        if filename:
            filename_lower = filename.lower()
            if any(term in filename_lower for term in ['10-k', '10k', '10-q', '10q', 'annual', 'quarterly']):
                return "prebuilt-layout"  # Best for structured financial documents
        
        if content_type == "application/pdf":
            return "prebuilt-layout"
        elif content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
            return "prebuilt-document"
        else:
            return "prebuilt-document"
    
    def _identify_financial_table_context(self, table) -> str:
        """Identify the financial context of a table based on its content"""
        sample_content = ""
        cell_count = 0
        
        for cell in table.cells:
            if cell_count >= 10:  # Sample first 10 cells
                break
            sample_content += cell.content.lower() + " "
            cell_count += 1
        
        financial_keywords = {
            "income_statement": ["revenue", "income", "expense", "profit", "loss", "earnings"],
            "balance_sheet": ["assets", "liabilities", "equity", "cash", "inventory", "debt"],
            "cash_flow": ["cash flow", "operating", "investing", "financing", "cash"],
            "financial_ratios": ["ratio", "margin", "return", "percentage", "%"]
        }
        
        for context, keywords in financial_keywords.items():
            if any(keyword in sample_content for keyword in keywords):
                return context
        
        return "general"
    
    def _score_financial_relevance(self, key: str, value: str) -> float:
        """Score the financial relevance of a key-value pair"""
        financial_terms = [
            "revenue", "income", "profit", "loss", "assets", "liabilities", "equity",
            "cash", "debt", "earnings", "dividend", "share", "stock", "market",
            "financial", "fiscal", "quarter", "annual", "year", "period"
        ]
        
        combined_text = (key + " " + value).lower()
        matches = sum(1 for term in financial_terms if term in combined_text)
        
        return min(matches / len(financial_terms), 1.0)
    
    def _identify_financial_sections(self, content: str, filename: str = None) -> List[Dict]:
        """Identify financial document sections in the content"""
        sections = []
        content_lower = content.lower()
        
        section_patterns = {
            "executive_summary": ["executive summary", "management discussion", "md&a"],
            "financial_statements": ["financial statements", "consolidated statements"],
            "income_statement": ["income statement", "statement of operations", "profit and loss"],
            "balance_sheet": ["balance sheet", "statement of financial position"],
            "cash_flow": ["cash flow statement", "statement of cash flows"],
            "notes": ["notes to financial statements", "footnotes"],
            "risk_factors": ["risk factors", "risks and uncertainties"]
        }
        
        for section_type, patterns in section_patterns.items():
            for pattern in patterns:
                if pattern in content_lower:
                    position = content_lower.find(pattern)
                    sections.append({
                        "type": section_type,
                        "pattern": pattern,
                        "position": position,
                        "confidence": 0.8  # Base confidence for pattern matching
                    })
                    break
        
        return sections

    async def save_session_history(self, session_id: str, message: Dict) -> bool:
        """Save chat session history to CosmosDB"""
        try:
            database = self.cosmos_client.get_database_client(settings.AZURE_COSMOS_DATABASE_NAME)
            container = database.get_container_client(settings.AZURE_COSMOS_CONTAINER_NAME)
            
            try:
                session_doc = container.read_item(item=session_id, partition_key=session_id)
            except:
                session_doc = {
                    "id": session_id,
                    "messages": [],
                    "created_at": message.get("timestamp"),
                    "updated_at": message.get("timestamp")
                }
            session_doc["messages"].append(message)
            session_doc["updated_at"] = message.get("timestamp")
            
            container.upsert_item(session_doc)
            logger.info(f"Session {session_id} updated in CosmosDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session history: {e}")
            return False

    async def get_session_history(self, session_id: str) -> List[Dict]:
        """Retrieve chat session history from CosmosDB"""
        try:
            database = self.cosmos_client.get_database_client(settings.AZURE_COSMOS_DATABASE_NAME)
            container = database.get_container_client(settings.AZURE_COSMOS_CONTAINER_NAME)
            
            try:
                session_doc = container.read_item(item=session_id, partition_key=session_id)
                return session_doc.get("messages", [])
            except Exception as e:
                # Session doesn't exist yet, return empty history
                if "NotFound" in str(e) or "does not exist" in str(e):
                    logger.info(f"Session {session_id} not found, returning empty history")
                    return []
                else:
                    # Some other error occurred
                    logger.error(f"Failed to retrieve session history: {e}")
                    return []
        except Exception as e:
            logger.error(f"Failed to retrieve session history: {e}")
            return []

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Retrieve available model deployments from Azure AI Foundry project with caching"""
        import time
        
        # Check cache first
        current_time = time.time()
        if (self._models_cache is not None and 
            self._models_cache_time is not None and 
            current_time - self._models_cache_time < self._cache_ttl):
            logger.debug("Returning cached models")
            return self._models_cache
        
        try:
            # with observability.trace_operation("azure_get_available_models") as span:
            if not self.project_client:
                logger.warning("Project client not initialized, returning mock models")
                # span.set_attribute("using_mock", True)
                return self._get_mock_models()
            
            connections = await self._get_project_connections_internal()
            models: List[Dict[str, Any]] = []
            
            for connection in connections:
                if connection.get("connection_type") == ConnectionType.AZURE_OPEN_AI or connection.get("type") == "azure_openai":
                    try:
                        connection_models = await self._get_models_from_connection(connection)
                        models.extend(connection_models)
                    except Exception as e:
                        logger.error(f"Failed to get models from connection {connection.get('name')}: {e}")
            
            # Merge deployments from direct Azure OpenAI inference endpoint if configured
            try:
                aoai_models = await self._list_aoai_deployments_via_inference()
                if aoai_models:
                    models.extend(aoai_models)
            except Exception as e:
                logger.warning(f"Could not list AOAI deployments via inference endpoint: {e}")

            if not models:
                logger.warning("No models found from connections or AOAI endpoint, using direct Azure OpenAI configuration")
                models = await self._get_models_from_direct_config()
            
            # Remove duplicates based on deployment name/id
            unique_models = []
            seen_ids = set()
            for model in models:
                model_id = model.get('id') or model.get('deployment_name')
                if model_id and model_id not in seen_ids:
                    unique_models.append(model)
                    seen_ids.add(model_id)
            
            logger.info(f"Returning {len(unique_models)} unique models (removed {len(models) - len(unique_models)} duplicates)")
            
            # Cache the result
            self._models_cache = unique_models
            self._models_cache_time = current_time
            
            # span.set_attribute("models_count", len(unique_models))
            # span.set_attribute("success", True)
            return unique_models
                
        except Exception as e:
            logger.error(f"Failed to retrieve available models: {e}")
            observability.record_error("azure_get_models_error", str(e))
            # Return cached result if available, otherwise mock models
            if self._models_cache is not None:
                logger.info("Returning cached models due to error")
                return self._models_cache
            return self._get_mock_models()
    
    def _get_mock_models(self) -> List[Dict[str, Any]]:
        """Get mock models for development/fallback"""
        return [
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "type": "chat",
                "version": "0613",
                "status": "active",
                "provider": "Azure OpenAI",
                "capabilities": ["chat", "completion"]
            },
            {
                "id": "gpt-35-turbo",
                "name": "GPT-3.5 Turbo",
                "type": "chat",
                "version": "0613",
                "status": "active",
                "provider": "Azure OpenAI",
                "capabilities": ["chat", "completion"]
            },
            {
                "id": "text-embedding-ada-002",
                "name": "Text Embedding Ada 002",
                "type": "embedding",
                "version": "2",
                "status": "active",
                "provider": "Azure OpenAI",
                "capabilities": ["embeddings"],
                "dimensions": 1536
            }
        ]
    
    async def _get_models_from_connection(self, connection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get model deployments from a specific Azure OpenAI connection"""
        try:
            connection_name = connection.get("name", "unknown")
            endpoint = connection.get("endpoint", "")

            # Try to enumerate deployments from this connection's endpoint
            deployments: List[Dict[str, Any]] = []
            try:
                direct = await self._list_aoai_deployments_via_inference(endpoint_override=endpoint)
                for m in direct:
                    m["connection"] = connection_name
                    m["endpoint"] = endpoint
                deployments.extend(direct)
            except Exception as e:
                logger.debug(f"Connection {connection_name} inference listing failed: {e}")

            return deployments
        except Exception as e:
            logger.error(f"Error getting models from connection {connection.get('name')}: {e}")
            return []

    async def get_project_connections(self) -> List[Dict[str, Any]]:
        """Retrieve project connections from Azure AI Foundry"""
        try:
            # with observability.trace_operation("azure_get_project_connections") as span:
                connections = await self._get_project_connections_internal()
            # span.set_attribute("connections_count", len(connections))
            # span.set_attribute("success", True)
                return connections
        except Exception as e:
            logger.error(f"Failed to retrieve project connections: {e}")
            observability.record_error("azure_get_connections_error", str(e))
            return []
    
    async def _get_project_connections_internal(self) -> List[Dict[str, Any]]:
        """Internal method to get project connections"""
        try:
            if not self.project_client:
                logger.warning("Project client not initialized, returning mock connections")
                return [
                    {
                        "name": "mock-azure-openai",
                        "type": "azure_openai",
                        "connection_type": ConnectionType.AZURE_OPEN_AI,
                        "status": "connected",
                        "endpoint": "https://mock-openai.openai.azure.com/"
                    }
                ]
            
            # Use the project client to list connections
            connections = self.project_client.connections.list()
            
            formatted_connections = []
            for conn in connections:
                formatted_connections.append({
                    "name": conn.name if hasattr(conn, 'name') else conn.get("name"),
                    "type": conn.connection_type.value if hasattr(conn, 'connection_type') else conn.get("type"),
                    "connection_type": conn.connection_type if hasattr(conn, 'connection_type') else conn.get("connection_type"),
                    "status": "connected",  # Assume connected if listed
                    "endpoint": conn.target if hasattr(conn, 'target') else conn.get("endpoint"),
                    "resource_id": conn.id if hasattr(conn, 'id') else conn.get("resource_id")
                })
            
            return formatted_connections
            
        except Exception as e:
            logger.error(f"Error getting project connections: {e}")
            return [
                {
                    "name": "fallback-azure-openai",
                    "type": "azure_openai",
                    "connection_type": ConnectionType.AZURE_OPEN_AI,                    "status": "connected",
                    "endpoint": "https://fallback-openai.openai.azure.com/"
                }
            ]

    async def get_project_info(self) -> Dict[str, Any]:
        """Get Azure AI Foundry project information"""
        try:
            # with observability.trace_operation("azure_get_project_info") as span:
            if not self.project_client:
                # span.set_attribute("using_mock", True)
                return {
                    "project_name": "mock-project",
                    "resource_group": "mock-rg",
                    "subscription_id": "mock-subscription",
                    "endpoint": "https://mock-project.cognitiveservices.azure.com/",
                    "status": "mock",
                    "client_type": "mock"
                }
            
            project_info = {
                "project_name": getattr(settings, 'AZURE_AI_FOUNDRY_PROJECT_NAME', 'unknown'),
                "resource_group": getattr(settings, 'AZURE_AI_FOUNDRY_RESOURCE_GROUP', 'unknown'),
                "subscription_id": getattr(settings, 'AZURE_SUBSCRIPTION_ID', 'unknown'),
                "endpoint": getattr(settings, 'AZURE_AI_PROJECT_ENDPOINT', 'unknown'),
                "status": "active",
                "client_type": "project_based"
            }
            
            try:
                connections = await self.get_project_connections()
                models = await self.get_available_models()
                project_info.update({
                    "connections_count": len(connections),
                    "models_count": len(models),
                    "connections": [conn.get("name") for conn in connections[:5]]  # First 5 connection names
                })
            except Exception as e:
                logger.warning(f"Could not get connection/model counts: {e}")
                project_info.update({
                    "connections_count": 0,
                    "models_count": 0
                })
            
            # span.set_attribute("project_name", project_info["project_name"])
            # span.set_attribute("connections_count", project_info.get("connections_count", 0))
            # span.set_attribute("success", True)
            
            return project_info
            
        except Exception as e:
            logger.error(f"Failed to get project info: {e}")
            observability.record_error("azure_get_project_info_error", str(e))
            return {"error": str(e), "status": "error"}

    async def _get_models_from_direct_config(self) -> List[Dict[str, Any]]:
        """Get models from Azure OpenAI Management API or fallback to direct configuration"""
        models = []
        
        try:
            # First try to get models from Azure OpenAI Management API
            if (settings.AZURE_OPENAI_ENDPOINT and 
                settings.AZURE_SUBSCRIPTION_ID and 
                settings.AZURE_AI_FOUNDRY_RESOURCE_GROUP):
                
                logger.info("Attempting to fetch models from Azure OpenAI Management API")
                
                # Use mock service in development, real service in production
                use_mock = os.getenv("MOCK_AZURE_SERVICES", "false").lower() == "true"
                service_class = MockAzureOpenAIDeploymentService if use_mock else AzureOpenAIDeploymentService
                
                async with service_class(settings) as deployment_service:
                    deployments = await deployment_service.get_deployments()
                    
                    for deployment in deployments:
                        models.append({
                            "id": deployment.deployment_name,
                            "name": f"{deployment.model_name} ({deployment.deployment_name})",
                            "deployment_name": deployment.deployment_name,
                            "model_name": deployment.model_name,
                            "model_version": deployment.model_version,
                            "type": deployment.model_type,
                            "status": "active" if deployment.provisioning_state == "Succeeded" else "inactive",
                            "provider": "Azure OpenAI (Management API)",
                            "capabilities": ["chat", "completion"] if deployment.model_type == "chat" else ["embedding"],
                            "endpoint": settings.AZURE_OPENAI_ENDPOINT,
                            "sku": deployment.sku_name,
                            "capacity": deployment.capacity,
                            "provisioning_state": deployment.provisioning_state
                        })
                    
                    if models:
                        logger.info(f"Successfully fetched {len(models)} models from Azure OpenAI Management API")
                        return models
                    else:
                        logger.warning("No deployments found from Management API, falling back to direct config")
        
        except Exception as e:
            logger.warning(f"Failed to fetch models from Management API: {e}, falling back to direct config")
        
        # Fallback to direct configuration if Management API fails. Try inference API first
        if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
            logger.info("Using AOAI inference endpoint to list deployments as fallback")
            try:
                direct = await self._list_aoai_deployments_via_inference()
                models.extend(direct)
            except Exception as e:
                logger.warning(f"Inference listing failed, falling back to configured names: {e}")
                # Last resort: include configured deployment names
                if settings.AZURE_OPENAI_DEPLOYMENT_NAME:
                    models.append({
                        "id": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                        "name": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                        "deployment_name": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                        "model_name": "Unknown",
                        "type": "chat",
                        "status": "active",
                        "provider": "Azure OpenAI (Direct Config Fallback)",
                        "capabilities": ["chat"],
                        "endpoint": settings.AZURE_OPENAI_ENDPOINT
                    })
                if settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME:
                    models.append({
                        "id": settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME,
                        "name": settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME,
                        "deployment_name": settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME,
                        "model_name": "Unknown",
                        "type": "embedding",
                        "status": "active",
                        "provider": "Azure OpenAI (Direct Config Fallback)",
                        "capabilities": ["embedding"],
                        "endpoint": settings.AZURE_OPENAI_ENDPOINT
                    })
        
        if not models:
            logger.warning("No Azure OpenAI configuration found, returning mock models")
            return self._get_mock_models()
            
        logger.info(f"Found {len(models)} models from direct Azure OpenAI configuration")
        return models

    async def _list_aoai_deployments_via_inference(self, endpoint_override: Optional[str] = None) -> List[Dict[str, Any]]:
        """List deployments from Azure OpenAI inference endpoint and normalize to unified schema."""
        endpoint = (endpoint_override or settings.AZURE_OPENAI_ENDPOINT or "").rstrip('/')
        if not endpoint or not settings.AZURE_OPENAI_API_KEY:
            return []
        api_version = settings.AZURE_OPENAI_API_VERSION or "2024-02-15-preview"
        url = f"{endpoint}/openai/deployments?api-version={api_version}"
        headers = {"api-key": settings.AZURE_OPENAI_API_KEY}
        deployments: List[Dict[str, Any]] = []
        
        # Use proper session management to prevent leaks
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("data") or data.get("value") or []
                for d in items:
                    dep_name = d.get("id") or d.get("name") or d.get("deployment_name")
                    model_name = (d.get("model") or d.get("model_name") or "").lower()
                    mtype = self._classify_model_type(model_name)
                    entry: Dict[str, Any] = {
                        "id": dep_name,
                        "name": dep_name,
                        "deployment_name": dep_name,
                        "model_name": model_name,
                    "type": mtype,
                    "status": d.get("status") or "active",
                    "provider": "Azure OpenAI",
                    "capabilities": ["embeddings"] if mtype == "embedding" else ["chat"],
                    "endpoint": endpoint,
                }
                if mtype == "embedding":
                    entry["dimensions"] = self._infer_embedding_dimensions(model_name)
                deployments.append(entry)
            except Exception as e:
                logger.warning(f"Failed to get inference endpoint deployments: {e}")
        return deployments

    def _classify_model_type(self, model_name: str) -> str:
        mn = (model_name or "").lower()
        if "embedding" in mn or mn.startswith("text-embedding"):
            return "embedding"
        return "chat"

    def _infer_embedding_dimensions(self, model_name: str) -> int:
        mn = (model_name or "").lower()
        if "text-embedding-3-large" in mn:
            return 3072
        if "text-embedding-3-small" in mn or "text-embedding-ada-002" in mn:
            return 1536
        return 1536

    async def recreate_search_index(self, force: bool = False) -> bool:
        """
        Force recreate the search index with the latest schema.
        This will delete the existing index and create a new one.
        Use with caution as this will delete all existing data.
        
        Args:
            force: If True, will delete existing index without checking
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not force:
                logger.warning("recreate_search_index() will DELETE all existing data. Call with force=True to proceed.")
                return False
                
            logger.info(f"Force recreating search index '{settings.AZURE_SEARCH_INDEX_NAME}'")
            
            # Delete existing index if it exists
            try:
                self.search_index_client.delete_index(settings.AZURE_SEARCH_INDEX_NAME)
                logger.info(f"Deleted existing index '{settings.AZURE_SEARCH_INDEX_NAME}'")
            except Exception as e:
                logger.info(f"No existing index to delete: {e}")
            
            # Create fresh index using ensure_search_index_exists
            return await self.ensure_search_index_exists()
            
        except Exception as e:
            logger.error(f"Failed to recreate search index: {e}")
            return False

    async def upload_document_to_storage(self, content: bytes, filename: str, document_id: str) -> str:
        """Upload document to Azure Storage and return the URL"""
        try:
            logger.info(f"Uploading document {document_id} ({filename}) to Azure Storage...")
              # Use the existing storage manager
            if hasattr(self, 'storage_manager') and self.storage_manager:
                blob_name = f"{document_id}/{filename}"
                storage_result = await self.storage_manager.upload_document(
                    file_content=content,
                    filename=blob_name,
                    content_type="application/pdf"  # Default to PDF, could be made dynamic
                )
                storage_url = storage_result.get('url', storage_result.get('blob_url'))
                logger.info(f"Document uploaded to storage successfully: {storage_url}")
                return storage_url
            else:
                logger.warning("Storage manager not available, skipping storage upload")
                return None
                
        except Exception as e:
            logger.error(f"Failed to upload document to storage: {e}")
            raise

    async def check_document_exists(self, accession_number: str) -> bool:
        """Check if a document with the given accession number already exists in the search index"""
        try:
            logger.info(f"Checking if document exists in index: {accession_number}")
            
            # Search for documents with the specific accession number using async client
            search_results = await self.search_client.search(
                search_text="*",
                filter=f"accession_number eq '{accession_number}'",
                select=["id", "accession_number"],
                top=1
            )
            
            # Convert async results to list to check if any documents exist
            documents = []
            async for result in search_results:
                documents.append(result)
                
            exists = len(documents) > 0
            
            if exists:
                logger.info(f"Document with accession number {accession_number} already exists in index")
            else:
                logger.info(f"Document with accession number {accession_number} not found in index")
                
            return exists
            
        except Exception as e:
            logger.error(f"Error checking if document exists: {e}")
            # In case of error, assume document doesn't exist to allow processing
            return False

    async def save_evaluation_result(self, evaluation_result: Dict[str, Any]) -> bool:
        """Save evaluation result to CosmosDB"""
        try:
            database = self.cosmos_client.get_database_client(settings.AZURE_COSMOS_DATABASE_NAME)
            container = database.get_container_client(settings.AZURE_COSMOS_EVALUATION_CONTAINER_NAME)
            
            # Prepare the document for storage
            evaluation_doc = {
                "id": evaluation_result.get("id"),
                "question_id": evaluation_result.get("question_id"),
                "session_id": evaluation_result.get("session_id"),
                "evaluator_type": evaluation_result.get("evaluator_type"),
                "rag_method": evaluation_result.get("rag_method"),
                "evaluation_model": evaluation_result.get("evaluation_model"),
                "question": evaluation_result.get("question"),
                "answer": evaluation_result.get("answer"),
                "context": evaluation_result.get("context"),
                "ground_truth": evaluation_result.get("ground_truth"),
                "groundedness_score": evaluation_result.get("groundedness_score"),
                "relevance_score": evaluation_result.get("relevance_score"),
                "coherence_score": evaluation_result.get("coherence_score"),
                "fluency_score": evaluation_result.get("fluency_score"),
                "similarity_score": evaluation_result.get("similarity_score"),
                "f1_score": evaluation_result.get("f1_score"),
                "bleu_score": evaluation_result.get("bleu_score"),
                "rouge_score": evaluation_result.get("rouge_score"),
                "overall_score": evaluation_result.get("overall_score"),
                "detailed_scores": evaluation_result.get("detailed_scores"),
                "reasoning": evaluation_result.get("reasoning"),
                "feedback": evaluation_result.get("feedback"),
                "recommendations": evaluation_result.get("recommendations"),
                "metadata": evaluation_result.get("metadata"),
                "error_message": evaluation_result.get("error_message"),
                "evaluation_timestamp": evaluation_result.get("evaluation_timestamp"),
                "evaluation_duration_ms": evaluation_result.get("evaluation_duration_ms"),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Convert datetime objects to ISO format strings for JSON serialization
            if evaluation_doc["evaluation_timestamp"] and hasattr(evaluation_doc["evaluation_timestamp"], 'isoformat'):
                evaluation_doc["evaluation_timestamp"] = evaluation_doc["evaluation_timestamp"].isoformat()
            
            container.upsert_item(evaluation_doc)
            logger.info(f"Evaluation result {evaluation_result.get('id')} saved to CosmosDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save evaluation result: {e}")
            return False

    async def get_evaluation_result(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve evaluation result from CosmosDB"""
        try:
            database = self.cosmos_client.get_database_client(settings.AZURE_COSMOS_DATABASE_NAME)
            container = database.get_container_client(settings.AZURE_COSMOS_EVALUATION_CONTAINER_NAME)
            
            # Since partition key is session_id, we need to query by evaluation_id instead of direct read
            query = "SELECT * FROM c WHERE c.id = @evaluation_id"
            parameters = [{"name": "@evaluation_id", "value": evaluation_id}]
            
            try:
                items = list(container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                    max_item_count=1
                ))
                
                if items:
                    logger.info(f"Retrieved evaluation result {evaluation_id} from CosmosDB")
                    return items[0]
                else:
                    logger.info(f"Evaluation result {evaluation_id} not found in CosmosDB")
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to retrieve evaluation result {evaluation_id}: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve evaluation result: {e}")
            return None

    async def list_evaluation_results(self, session_id: Optional[str] = None, question_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List evaluation results with optional filtering"""
        try:
            database = self.cosmos_client.get_database_client(settings.AZURE_COSMOS_DATABASE_NAME)
            container = database.get_container_client(settings.AZURE_COSMOS_EVALUATION_CONTAINER_NAME)
            
            # Build query based on filters
            if session_id:
                query = "SELECT * FROM c WHERE c.session_id = @session_id ORDER BY c.evaluation_timestamp DESC"
                parameters = [{"name": "@session_id", "value": session_id}]
            elif question_id:
                query = "SELECT * FROM c WHERE c.question_id = @question_id ORDER BY c.evaluation_timestamp DESC"
                parameters = [{"name": "@question_id", "value": question_id}]
            else:
                query = "SELECT * FROM c ORDER BY c.evaluation_timestamp DESC"
                parameters = []
            
            items = list(container.query_items(
                query=query,
                parameters=parameters,
                max_item_count=limit,
                enable_cross_partition_query=True
            ))
            
            logger.info(f"Retrieved {len(items)} evaluation results from CosmosDB")
            return items
            
        except Exception as e:
            logger.error(f"Failed to list evaluation results: {e}")
            return []

    async def delete_evaluation_results(self, session_id: str) -> int:
        """Delete evaluation results for a session"""
        try:
            database = self.cosmos_client.get_database_client(settings.AZURE_COSMOS_DATABASE_NAME)
            container = database.get_container_client(settings.AZURE_COSMOS_EVALUATION_CONTAINER_NAME)
            
            # Query for evaluation results in the session
            query = "SELECT c.id FROM c WHERE c.session_id = @session_id"
            parameters = [{"name": "@session_id", "value": session_id}]
            
            items = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            deleted_count = 0
            for item in items:
                try:
                    # Use session_id as partition key since that's what the container is configured with
                    container.delete_item(item=item["id"], partition_key=session_id)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete evaluation result {item['id']}: {e}")
            
            logger.info(f"Deleted {deleted_count} evaluation results for session {session_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting evaluation results: {e}")
            return 0
