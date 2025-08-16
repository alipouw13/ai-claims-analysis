from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    
    AZURE_SEARCH_SERVICE_NAME: str = ""
    AZURE_SEARCH_INDEX_NAME: str = "financial-documents"
    # Separate indexes for policy documents vs claim documents
    AZURE_SEARCH_POLICY_INDEX_NAME: str = "rag-policy"
    AZURE_SEARCH_CLAIMS_INDEX_NAME: str = "rag-claims"
    AZURE_SEARCH_QUERY_BOTH_INDEXES: bool = True
    AZURE_SEARCH_API_VERSION: str = "2023-11-01"
    AZURE_SEARCH_API_KEY: str = ""
    
    # Additional Azure AI Search configurations for Agentic RAG
    AZURE_SEARCH_AGENT_NAME: str = "financial-qa-agent"
    AZURE_OPENAI_CHAT_MODEL_NAME: str = "gpt-4o-mini"
    
    @property
    def AZURE_AI_SEARCH_ENDPOINT(self) -> str:
        """Compute Azure AI Search endpoint from service name"""
        if self.AZURE_SEARCH_SERVICE_NAME:
            return f"https://{self.AZURE_SEARCH_SERVICE_NAME}.search.windows.net"
        return ""
    
    @property 
    def AZURE_AI_SEARCH_INDEX_NAME(self) -> str:
        """Alias for backward compatibility"""
        return self.AZURE_SEARCH_INDEX_NAME
    
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-01"
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: str = "chat4omini"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME: str = "text-embedding-ada-002"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "chat4omini"
    
    AVAILABLE_EMBEDDING_MODELS: List[str] = [
        "text-embedding-ada-002",
        "text-embedding-3-small", 
        "text-embedding-3-large"
    ]
    AVAILABLE_CHAT_MODELS: List[str] = [
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",  # Supported for agentic retrieval
        "gpt-4o-mini",  # Supported for agentic retrieval
        "gpt-4.1",  # Supported for agentic retrieval
        "gpt-4.1-nano",  # Supported for agentic retrieval
        "gpt-4.1-mini",  # Supported for agentic retrieval
        "gpt-35-turbo",
        "financial-llm",  # Industry specific
        "grok-beta",
        "deepseek-chat"
    ]
    
    AZURE_COSMOS_ENDPOINT: str = ""
    AZURE_COSMOS_DATABASE_NAME: str = "rag-financial-db"
    AZURE_COSMOS_CONTAINER_NAME: str = "chat-sessions"
    AZURE_COSMOS_EVALUATION_CONTAINER_NAME: str = "evaluation-results"
    AZURE_COSMOS_TOKEN_USAGE_CONTAINER_NAME: str = "token-usage"
    
    AZURE_FORM_RECOGNIZER_ENDPOINT: str = ""
    
    AZURE_AI_FOUNDRY_PROJECT_NAME: str = ""
    AZURE_AI_FOUNDRY_RESOURCE_GROUP: str = ""
    AZURE_SUBSCRIPTION_ID: str = ""
    AZURE_AI_FOUNDRY_WORKSPACE_NAME: str = ""
    # Support multiple aliases for AI Foundry endpoint to avoid configuration mismatches
    AZURE_AI_PROJECT_ENDPOINT: str = ""
    # Bing Search configuration (for web grounding fallback)
    BING_SEARCH_ENDPOINT: str = "https://api.bing.microsoft.com/v7.0/search"
    BING_SEARCH_SUBSCRIPTION_KEY: Optional[str] = None
    # Azure Speech Services (server STT)
    AZURE_SPEECH_KEY: Optional[str] = None
    AZURE_SPEECH_REGION: Optional[str] = None
    # Azure Monitor and Application Insights Configuration
    azure_monitor_connection_string: str = ""
    azure_key_vault_url: str = ""
    enable_telemetry: bool = False
    
    mcp_enabled: bool = True
    mcp_server_port: int = 3001
    a2a_enabled: bool = True
    a2a_discovery_endpoint: str = "https://your-a2a-discovery.azure.com/"
    
    max_document_size_mb: int = 50
    supported_document_types: str = "pdf,docx,xlsx,txt"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunks_per_document: int = 500
    
    # Evaluation Configuration
    AZURE_EVALUATION_ENDPOINT: str = ""
    AZURE_EVALUATION_API_KEY: str = ""
    AZURE_EVALUATION_MODEL_DEPLOYMENT: str = "gpt-4o-mini"
    AZURE_EVALUATION_MODEL_NAME: str = "gpt-4o-mini"
    
    # Azure AI Foundry Configuration for Evaluation
    AZURE_AI_PROJECT_CONNECTION_STRING: str = ""
    AZURE_AI_PROJECT_NAME: str = ""
    AZURE_AI_HUB_NAME: str = ""
    
    # Evaluation Settings
    EVALUATION_ENABLED: bool = True
    DEFAULT_EVALUATOR_TYPE: str = "custom"  # "foundry" or "custom"
    
    AVAILABLE_EVALUATOR_TYPES: List[str] = ["foundry", "custom"]
    AVAILABLE_EVALUATION_MODELS: List[str] = [
        "o3-mini",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4"
    ]
    
    rate_limit_requests_per_minute: int = 100
    rate_limit_tokens_per_minute: int = 50000
    
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600
    
    jwt_secret_key: str = "your-jwt-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_KEY: Optional[str] = None
    AZURE_STORAGE_CONTAINER_NAME: str = "financial-documents"
    
    mock_azure_services: bool = False
    enable_debug_logging: bool = False
    enable_performance_profiling: bool = False
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # MCP (Model Context Protocol) Configuration
    MCP_SERVER_URL: Optional[str] = None
    MCP_SERVER_TIMEOUT: int = 30
    
    # Additional constants (not environment-configurable)
    MAX_TOKENS_PER_REQUEST: int = 4000
    TEMPERATURE: float = 0.1
    
    AUTO_UPDATE_ENABLED: bool = True
    UPDATE_FREQUENCY_HOURS: int = 24
    CREDIBILITY_THRESHOLD: float = 0.7
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # Allow extra fields to prevent validation errors

settings = Settings()
