# Agent Deployment with Tools - Azure AI Foundry Integration

This document describes the new agent deployment structure that integrates Azure AI Foundry agents with tools for enhanced functionality.

## Overview

The application has been restructured to deploy Azure AI Foundry agents with integrated tools including:
- **Azure AI Search tools** for document retrieval and search
- **Bing Search tools** for web grounding and fact verification
- **Knowledge Base tools** for managing policies and claims

## Folder Structure

```
backend/
├── agents/                          # Agent implementations
│   ├── __init__.py
│   ├── azure_ai_agent_service.py
│   ├── azure_ai_agent_service_insurance.py
│   ├── multi_agent_orchestrator.py
│   ├── multi_agent_insurance_orchestrator.py
│   ├── agentic_vector_rag_service.py
│   └── agent_deployment_service.py  # Agent deployment orchestration
├── agent-tools/                     # Agent tools
│   ├── __init__.py
│   ├── azure_search_tool.py         # Azure AI Search integration
│   ├── bing_search_tool.py          # Bing Search for grounding
│   └── knowledge_base_tool.py       # Knowledge base management
└── app/
    └── api/
        └── routes/
            └── agents.py            # Agent deployment API endpoints
```

## Agent Tools

### 1. Azure AI Search Tool (`azure_search_tool.py`)

Provides agents with access to Azure AI Search indexes for:
- Searching across multiple indexes (policy, claims, financial documents)
- Performing hybrid search (vector + keyword + semantic)
- Retrieving relevant documents and chunks
- Supporting agentic retrieval with query planning

**Capabilities:**
- `search_documents()` - Search across indexes
- `get_document_chunks()` - Retrieve document chunks
- `get_index_metrics()` - Get index statistics

### 2. Bing Search Tool (`bing_search_tool.py`)

Provides web grounding capabilities for:
- Web search for current information
- News search for market updates
- Fact verification against web sources
- Real-time information retrieval

**Capabilities:**
- `search_web()` - General web search
- `search_news()` - News-specific search
- `verify_facts()` - Fact verification

### 3. Knowledge Base Tool (`knowledge_base_tool.py`)

Provides knowledge base management for:
- Document operations and metadata
- Policy and claims management
- Knowledge base analytics
- Health monitoring

**Capabilities:**
- `get_knowledge_base_stats()` - Get KB statistics
- `list_documents()` - List documents
- `get_document_details()` - Get document details
- `search_knowledge_base()` - Search KB
- `get_knowledge_base_health()` - Health monitoring

## Agent Deployment

### Deployment Service (`agent_deployment_service.py`)

The `AgentDeploymentService` handles deploying agents with integrated tools:

```python
from app.agents.agent_deployment_service import AgentDeploymentService

# Initialize deployment service
deployment_service = AgentDeploymentService()
await deployment_service.initialize()

# Deploy financial QA agent
result = await deployment_service.deploy_financial_qa_agent("my-financial-agent")

# Deploy insurance agent
result = await deployment_service.deploy_insurance_agent("my-insurance-agent")
```

### Agent Types

#### 1. Financial QA Agent
- **Purpose**: Financial document analysis and Q&A
- **Tools**: Azure AI Search, Bing Search, Knowledge Base
- **Capabilities**: 
  - Search financial documents and SEC filings
  - Retrieve current market information
  - Analyze financial data and provide insights
  - Verify financial facts and figures

#### 2. Insurance Agent
- **Purpose**: Policy and claims management
- **Tools**: Azure AI Search, Knowledge Base
- **Capabilities**:
  - Search insurance policies and claims documents
  - Manage knowledge base operations
  - Provide policy information and claims assistance
  - Analyze insurance data and trends

## API Endpoints

### Agent Deployment Endpoints

```
POST /api/v1/agents/deploy/financial-qa
POST /api/v1/agents/deploy/insurance
POST /api/v1/agents/deploy/custom
GET  /api/v1/agents/list
GET  /api/v1/agents/status/{agent_name}
GET  /api/v1/agents/tools/schemas
```

### Example Usage

#### Deploy Financial QA Agent
```bash
curl -X POST "http://localhost:8000/api/v1/agents/deploy/financial-qa" \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "my-financial-agent"}'
```

#### Deploy Insurance Agent
```bash
curl -X POST "http://localhost:8000/api/v1/agents/deploy/insurance" \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "my-insurance-agent"}'
```

#### List Deployed Agents
```bash
curl -X GET "http://localhost:8000/api/v1/agents/list"
```

#### Get Agent Status
```bash
curl -X GET "http://localhost:8000/api/v1/agents/status/my-financial-agent"
```

## Configuration

### Required Environment Variables

```env
# Azure AI Foundry
AZURE_SUBSCRIPTION_ID=your_subscription_id
AZURE_AI_FOUNDRY_RESOURCE_GROUP=your_resource_group
AZURE_AI_FOUNDRY_WORKSPACE_NAME=your_workspace_name

# Azure AI Search
AZURE_SEARCH_SERVICE_NAME=your_search_service
AZURE_SEARCH_API_KEY=your_search_api_key
AZURE_SEARCH_POLICY_INDEX_NAME=policy-documents
AZURE_SEARCH_CLAIMS_INDEX_NAME=claims-documents

# Bing Search (for grounding)
BING_SEARCH_SUBSCRIPTION_KEY=your_bing_key
BING_SEARCH_ENDPOINT=https://api.bing.microsoft.com/v7.0/search
```

## Integration with Azure AI Foundry

The deployment follows Azure AI Foundry patterns as documented in:
[Azure AI Foundry Agents with Tools](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/azure-ai-search?tabs=pythonsdk)

### Key Features:
1. **Connection Management**: Automatic creation of Azure AI Search connections
2. **Tool Integration**: Seamless integration of tools with agents
3. **Agent Instructions**: Specialized instructions for different agent types
4. **Deployment Orchestration**: Automated deployment process

## Benefits

1. **Enhanced Capabilities**: Agents now have access to multiple data sources
2. **Web Grounding**: Real-time information via Bing Search
3. **Specialized Tools**: Domain-specific tools for financial and insurance use cases
4. **Scalable Architecture**: Modular tool system for easy extension
5. **Azure AI Foundry Integration**: Native integration with Azure AI Foundry platform

## Next Steps

1. **Deploy Agents**: Use the API endpoints to deploy agents with tools
2. **Configure Tools**: Ensure all required environment variables are set
3. **Test Integration**: Verify agents can access and use the tools
4. **Monitor Performance**: Use Azure AI Foundry portal to monitor agent performance

## Troubleshooting

### Common Issues

1. **Missing Azure AI ML SDK**: Install with `pip install azure-ai-ml`
2. **Configuration Errors**: Verify all environment variables are set
3. **Connection Failures**: Check Azure AI Foundry workspace access
4. **Tool Initialization**: Ensure Azure services are properly configured

### Debug Mode

Enable debug logging to troubleshoot deployment issues:

```python
import logging
logging.getLogger("app.agents").setLevel(logging.DEBUG)
logging.getLogger("app.agent_tools").setLevel(logging.DEBUG)
```
