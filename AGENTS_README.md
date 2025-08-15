# Agent System Documentation

## Overview

The Agentic RAG system implements a sophisticated multi-agent orchestration framework with domain-specific agents for insurance and financial document processing. The system leverages Microsoft Semantic Kernel for advanced orchestration and Azure AI Foundry for native agent deployment.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Agent Orchestrator                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Semantic Kernel │  │ Agent Registry  │  │ Event Bus    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain-Specific Agents                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │ Auto Agent  │ │ Life Agent  │ │Health Agent │ │Dental   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ │Agent    │ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ └─────────┘ │
│  │General Agent│ │Financial QA │ │Claims Agent │ ┌─────────┐ │
│  └─────────────┘ │Agent        │ └─────────────┘ │SEC Agent│ │
│                  └─────────────┘                 └─────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent Tools                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Azure Search    │  │ Bing Search     │  │ Knowledge    │ │
│  │ Tool            │  │ Tool            │  │ Base Tool    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Code Interpreter│  │ File Search     │                   │
│  │ Tool            │  │ Tool            │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Agent Types

### 1. Insurance Domain Agents

#### Auto Insurance Agent
- **Purpose**: Auto policy analysis and claims processing
- **Capabilities**:
  - Vehicle claims assessment and damage evaluation
  - Policy coverage verification and liability analysis
  - Accident reconstruction and fault determination
  - Premium calculation and rate analysis
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search
- **Indexes**: `claims-documents`, `policy-documents`

#### Life Insurance Agent
- **Purpose**: Life policy analysis and death claim processing
- **Capabilities**:
  - Life policy analysis and beneficiary verification
  - Death claim processing and documentation review
  - Underwriting assessment and risk evaluation
  - Policy valuation and cash value calculations
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search
- **Indexes**: `policy-documents`

#### Health Insurance Agent
- **Purpose**: Health policy analysis and medical claims processing
- **Capabilities**:
  - Medical claims processing and benefit verification
  - Preauthorization review and network analysis
  - Treatment plan evaluation and cost analysis
  - Healthcare provider network management
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search
- **Indexes**: `claims-documents`, `policy-documents`

#### Dental Insurance Agent
- **Purpose**: Dental policy analysis and dental claims processing
- **Capabilities**:
  - Dental claims processing and treatment plan review
  - Benefit verification and network analysis
  - Dental procedure cost analysis
  - Preventive care coordination
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search
- **Indexes**: `claims-documents`, `policy-documents`

#### General Insurance Agent (Fallback)
- **Purpose**: General policy analysis and claims processing
- **Capabilities**:
  - General policy analysis and risk assessment
  - Claims processing across multiple insurance types
  - Coverage analysis and policy recommendations
  - Web-based information retrieval and fact verification
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search, Bing Search
- **Indexes**: `claims-documents`, `policy-documents`

### 2. Financial Domain Agents

#### Financial QA Agent
- **Purpose**: Financial document analysis and Q&A
- **Capabilities**:
  - SEC document analysis (10-K, 10-Q, 8-K)
  - Financial metric extraction and analysis
  - Market data retrieval and analysis
  - Financial ratio calculations and benchmarking
- **Tools**: Azure Search, Bing Search, Knowledge Base, Code Interpreter
- **Indexes**: `financial-documents`

#### SEC Document Agent
- **Purpose**: Specialized SEC filing analysis
- **Capabilities**:
  - Deep analysis of SEC filings and financial statements
  - Risk factor identification and assessment
  - Corporate governance analysis
  - Regulatory compliance verification
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search
- **Indexes**: `financial-documents`

### 3. Claims Processing Agent

#### Claims Agent
- **Purpose**: Claims processing and assessment
- **Capabilities**:
  - Claims validation and documentation review
  - Damage assessment and cost estimation
  - Fraud detection and investigation
  - Settlement calculation and negotiation support
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search
- **Indexes**: `claims-documents`

## Agent Tools

### 1. Azure Search Tool (`azure_search_tool.py`)

Provides agents with access to Azure AI Search indexes for document retrieval and search.

**Capabilities**:
- `search_documents()` - Search across multiple indexes
- `get_document_chunks()` - Retrieve document chunks with metadata
- `get_index_metrics()` - Get index statistics and health
- `hybrid_search()` - Combined vector and keyword search
- `semantic_search()` - Semantic similarity search

**Configuration**:
```python
# Environment variables
AZURE_SEARCH_SERVICE_NAME=your_search_service
AZURE_SEARCH_API_KEY=your_search_api_key
AZURE_SEARCH_INDEX_NAME=financial-documents
AZURE_SEARCH_POLICY_INDEX_NAME=policy-documents
AZURE_SEARCH_CLAIMS_INDEX_NAME=claims-documents
```

### 2. Bing Search Tool (`bing_search_tool.py`)

Provides web grounding capabilities for real-time information retrieval.

**Capabilities**:
- `search_web()` - General web search
- `search_news()` - News-specific search
- `verify_facts()` - Fact verification against web sources
- `get_market_data()` - Real-time market information

**Configuration**:
```python
# Environment variables
BING_SEARCH_SUBSCRIPTION_KEY=your_bing_key
BING_SEARCH_ENDPOINT=https://api.bing.microsoft.com/v7.0/search
```

### 3. Knowledge Base Tool (`knowledge_base_tool.py`)

Provides knowledge base management and operations.

**Capabilities**:
- `get_knowledge_base_stats()` - Get KB statistics
- `list_documents()` - List documents in KB
- `get_document_details()` - Get document details
- `search_knowledge_base()` - Search KB content
- `get_knowledge_base_health()` - Health monitoring

### 4. Code Interpreter Tool (`code_interpreter_tool.py`)

Provides Python code execution for calculations and analysis.

**Capabilities**:
- `execute_python_code()` - Execute Python code safely
- `calculate_financial_ratios()` - Financial ratio calculations
- `analyze_data()` - Data analysis and visualization
- `generate_reports()` - Report generation

### 5. File Search Tool (`file_search_tool.py`)

Provides file search and retrieval capabilities.

**Capabilities**:
- `search_files()` - Search for files by content
- `get_file_content()` - Retrieve file content
- `analyze_document()` - Document content analysis
- `extract_metadata()` - Metadata extraction

## Multi-Agent Orchestration

### Semantic Kernel Integration

The system uses Microsoft Semantic Kernel for advanced orchestration and planning.

```python
from semantic_kernel import Kernel
from semantic_kernel.plugin_definition import sk_function

class InsuranceOrchestrator:
    def __init__(self, kernel: Kernel):
        self.kernel = kernel
        self.agent_registry = AgentRegistry()
    
    async def orchestrate_claim_processing(self, claim_data: dict):
        """Orchestrate multi-agent claim processing workflow"""
        
        # Create execution plan
        plan = await self.kernel.create_plan("""
        Process insurance claim with the following steps:
        1. Validate claim data and documentation
        2. Assess damage and calculate costs
        3. Verify policy coverage and benefits
        4. Determine liability and fault
        5. Calculate settlement amount
        6. Generate claim report
        """)
        
        # Execute plan with multiple agents
        results = await self.execute_plan_with_agents(plan, claim_data)
        return results
```

### Parallel Execution Strategy

The system supports both sequential and parallel execution patterns:

#### Sequential Execution
- Uses Semantic Kernel planner for step-by-step workflows
- Good for complex, dependent tasks
- Ensures proper task ordering and dependencies

#### Parallel Execution
- Multiple agents work simultaneously
- Faster execution for independent tasks
- Automatic result aggregation and conflict resolution

### Agent Coordination Patterns

#### 1. Scatter-Gather Pattern
```python
async def scatter_gather_analysis(self, query: str, documents: List[str]):
    """Distribute analysis across multiple agents and gather results"""
    
    # Scatter: Send to multiple agents
    tasks = [
        self.auto_agent.analyze_policy(query, documents),
        self.life_agent.analyze_policy(query, documents),
        self.health_agent.analyze_policy(query, documents)
    ]
    
    # Gather: Collect and aggregate results
    results = await asyncio.gather(*tasks)
    return self.aggregate_results(results)
```

#### 2. Pipeline Pattern
```python
async def pipeline_processing(self, document_id: str):
    """Process document through multiple agents in sequence"""
    
    # Step 1: Document processing
    processed_doc = await self.document_agent.process_document(document_id)
    
    # Step 2: Financial analysis
    financial_analysis = await self.financial_agent.analyze_document(processed_doc)
    
    # Step 3: Risk assessment
    risk_assessment = await self.risk_agent.assess_risks(financial_analysis)
    
    # Step 4: Knowledge base update
    await self.knowledge_agent.update_knowledge_base(risk_assessment)
    
    return risk_assessment
```

#### 3. Event-Driven Pattern
```python
class EventDrivenOrchestrator:
    def __init__(self):
        self.event_bus = EventBus()
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """Setup event handlers for agent coordination"""
        
        @self.event_bus.on("document_processed")
        async def handle_document_processed(event_data):
            await self.financial_agent.analyze_document(event_data["document_id"])
        
        @self.event_bus.on("analysis_completed")
        async def handle_analysis_completed(event_data):
            await self.knowledge_agent.update_knowledge_base(event_data["analysis"])
```

## Azure AI Foundry Integration

### Agent Deployment

The system integrates with Azure AI Foundry for native agent deployment:

```python
from app.services.agents.agent_deployment_service import AgentDeploymentService

# Initialize deployment service
deployment_service = AgentDeploymentService()

# Deploy insurance agent
result = await deployment_service.deploy_insurance_agent(
    agent_name="auto-insurance-agent",
    agent_type="auto",
    tools=["azure_search", "knowledge_base", "code_interpreter"]
)
```

### Tool Integration

Agents deployed through Azure AI Foundry have seamless access to tools:

```python
# Agent instructions with tool integration
AGENT_INSTRUCTIONS = """
You are an Auto Insurance Agent with access to the following tools:
- Azure Search Tool: Search insurance policies and claims
- Knowledge Base Tool: Access and manage knowledge base
- Code Interpreter Tool: Perform calculations and analysis

Use these tools to:
1. Search for relevant policies and claims
2. Analyze coverage and benefits
3. Calculate premiums and settlements
4. Generate reports and recommendations
"""
```

### Connection Management

The deployment service automatically manages Azure service connections:

```python
# Automatic connection creation
connections = await deployment_service.create_connections([
    {
        "name": "azure-search-connection",
        "type": "azure_ai_search",
        "config": {
            "service_name": settings.AZURE_SEARCH_SERVICE_NAME,
            "api_key": settings.AZURE_SEARCH_API_KEY
        }
    },
    {
        "name": "knowledge-base-connection", 
        "type": "knowledge_base",
        "config": {
            "endpoint": settings.KNOWLEDGE_BASE_ENDPOINT
        }
    }
])
```

## API Endpoints

### Agent Management

```
POST /api/v1/agents/deploy/financial-qa
POST /api/v1/agents/deploy/insurance
POST /api/v1/agents/deploy/custom
GET  /api/v1/agents/list
GET  /api/v1/agents/status/{agent_name}
DELETE /api/v1/agents/{agent_name}
```

### Agent Operations

```
POST /api/v1/agents/{agent_name}/analyze-policy
POST /api/v1/agents/{agent_name}/process-claim
POST /api/v1/agents/{agent_name}/answer-question
GET  /api/v1/agents/{agent_name}/tools/schemas
```

### Orchestration

```
POST /api/v1/insurance/orchestrate/policy-analysis
POST /api/v1/insurance/orchestrate/claims-processing
POST /api/v1/insurance/orchestrate/customer-support
GET  /api/v1/insurance/orchestrator/status
```

## Configuration

### Environment Variables

```bash
# Azure AI Foundry
AZURE_SUBSCRIPTION_ID=your_subscription_id
AZURE_AI_FOUNDRY_RESOURCE_GROUP=your_resource_group
AZURE_AI_FOUNDRY_WORKSPACE_NAME=your_workspace_name

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=your_openai_endpoint
AZURE_OPENAI_API_KEY=your_openai_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

# Azure Search
AZURE_SEARCH_SERVICE_NAME=your_search_service
AZURE_SEARCH_API_KEY=your_search_api_key
AZURE_SEARCH_INDEX_NAME=financial-documents
AZURE_SEARCH_POLICY_INDEX_NAME=policy-documents
AZURE_SEARCH_CLAIMS_INDEX_NAME=claims-documents

# Bing Search
BING_SEARCH_SUBSCRIPTION_KEY=your_bing_key
BING_SEARCH_ENDPOINT=https://api.bing.microsoft.com/v7.0/search

# Azure Authentication
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
```

### Agent Configuration

```python
# Agent configuration example
AGENT_CONFIG = {
    "auto_agent": {
        "type": "auto",
        "tools": ["azure_search", "knowledge_base", "code_interpreter", "file_search"],
        "indexes": ["claims-documents", "policy-documents"],
        "max_concurrent_requests": 10,
        "timeout_seconds": 300
    },
    "financial_qa_agent": {
        "type": "financial_qa",
        "tools": ["azure_search", "bing_search", "knowledge_base", "code_interpreter"],
        "indexes": ["financial-documents"],
        "max_concurrent_requests": 5,
        "timeout_seconds": 600
    }
}
```

## Usage Examples

### 1. Deploy Insurance Agent

```python
from app.services.agents.agent_deployment_service import AgentDeploymentService

# Initialize deployment service
deployment_service = AgentDeploymentService()
await deployment_service.initialize()

# Deploy auto insurance agent
result = await deployment_service.deploy_insurance_agent(
    agent_name="auto-insurance-specialist",
    agent_type="auto",
    tools=["azure_search", "knowledge_base", "code_interpreter"],
    instructions="You are an expert auto insurance agent..."
)

print(f"Agent deployed: {result['agent_name']}")
print(f"Status: {result['status']}")
```

### 2. Process Insurance Claim

```python
from app.services.agents.multi_agent_insurance_orchestrator import MultiAgentInsuranceOrchestrator

# Initialize orchestrator
orchestrator = MultiAgentInsuranceOrchestrator()

# Process auto insurance claim
claim_data = {
    "domain": "auto",
    "claim_type": "collision",
    "damage_estimate": 5000,
    "deductible": 500,
    "accident_details": {
        "date": "2024-01-15",
        "description": "Rear-end collision",
        "fault": "other_driver"
    }
}

result = await orchestrator.process_claim(claim_data)
print(f"Claim processed: {result['status']}")
print(f"Settlement amount: ${result['settlement_amount']}")
```

### 3. Multi-Agent Analysis

```python
# Analyze policy with multiple agents
analysis_request = {
    "domain": "auto",
    "policy_id": "POL-12345",
    "analysis_type": "comprehensive",
    "parallel_execution": True
}

results = await orchestrator.analyze_policy(analysis_request)

# Results from multiple agents
for agent_result in results['agent_results']:
    print(f"Agent: {agent_result['agent_name']}")
    print(f"Analysis: {agent_result['analysis']}")
    print(f"Confidence: {agent_result['confidence']}")
```

## Monitoring and Observability

### Agent Metrics

The system tracks comprehensive metrics for each agent:

- **Performance Metrics**: Response times, throughput, error rates
- **Resource Usage**: CPU, memory, and storage utilization
- **Tool Usage**: Tool call frequency and success rates
- **Quality Metrics**: Analysis accuracy and confidence scores

### Health Monitoring

```python
# Check agent health
health_status = await orchestrator.get_agent_health("auto-insurance-agent")

print(f"Status: {health_status['status']}")
print(f"Uptime: {health_status['uptime']}")
print(f"Last Activity: {health_status['last_activity']}")
print(f"Tool Status: {health_status['tool_status']}")
```

### Distributed Tracing

All agent interactions are traced using OpenTelemetry:

```python
# Trace agent workflow
with tracer.start_as_current_span("insurance_claim_processing") as span:
    span.set_attribute("claim_id", claim_data["claim_id"])
    span.set_attribute("domain", claim_data["domain"])
    
    # Process claim with tracing
    result = await orchestrator.process_claim(claim_data)
    
    span.set_attribute("result.status", result["status"])
    span.set_attribute("processing_time", result["processing_time"])
```

## Troubleshooting

### Common Issues

1. **Agent Initialization Failures**
   - Check environment variables and Azure service connectivity
   - Verify tool initialization and permissions
   - Review agent configuration and instructions

2. **Tool Access Issues**
   - Verify Azure service connections and API keys
   - Check tool permissions and access control
   - Review tool configuration and endpoints

3. **Orchestration Failures**
   - Check Semantic Kernel configuration
   - Verify agent registry and event bus setup
   - Review workflow definitions and dependencies

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging

# Enable debug logging
logging.getLogger("app.services.agents").setLevel(logging.DEBUG)
logging.getLogger("app.services.agent_tools").setLevel(logging.DEBUG)
logging.getLogger("semantic_kernel").setLevel(logging.DEBUG)
```

### Health Check Endpoints

```
GET /api/v1/agents/health
GET /api/v1/agents/{agent_name}/health
GET /api/v1/agents/tools/health
GET /api/v1/insurance/orchestrator/health
```

## Best Practices

### 1. Agent Design
- Keep agents focused on specific domains and capabilities
- Use clear, specific instructions for each agent
- Implement proper error handling and fallback mechanisms
- Design agents for reusability and composability

### 2. Tool Integration
- Use tools consistently across agents
- Implement proper tool access control
- Cache tool results when appropriate
- Monitor tool usage and performance

### 3. Orchestration
- Use appropriate execution patterns (sequential vs parallel)
- Implement proper result aggregation and conflict resolution
- Design workflows for fault tolerance and recovery
- Monitor orchestration performance and bottlenecks

### 4. Deployment
- Use Azure AI Foundry for production deployments
- Implement proper connection management
- Monitor agent health and performance
- Use versioning for agent updates

## Future Enhancements

### Planned Features

1. **Dynamic Agent Discovery**
   - Automatic discovery and registration of new agents
   - Load balancing and agent selection optimization
   - Dynamic agent scaling based on workload

2. **Advanced Orchestration**
   - Machine learning-powered workflow optimization
   - Adaptive agent selection based on query complexity
   - Intelligent resource allocation and scheduling

3. **Enhanced Tools**
   - Document processing and analysis tools
   - Image and video analysis capabilities
   - Voice processing and transcription tools

4. **Security Enhancements**
   - Enhanced access control and authentication
   - Data encryption and privacy protection
   - Audit logging and compliance features

### Integration Roadmap

1. **Azure AI Foundry Enhancements**
   - Native tool marketplace integration
   - Advanced orchestration capabilities
   - Enhanced monitoring and observability

2. **MCP Protocol Extensions**
   - Real-time streaming capabilities
   - Advanced A2A communication patterns
   - Cross-platform agent interoperability

3. **Semantic Kernel Integration**
   - Advanced planning and reasoning capabilities
   - Dynamic workflow generation
   - Intelligent agent coordination

## Conclusion

The agent system provides a robust, scalable foundation for building sophisticated insurance and financial analysis applications. With domain-specific agents, advanced orchestration, and seamless tool integration, the system can handle complex workflows while maintaining high performance and reliability.

The integration with Azure AI Foundry and Semantic Kernel ensures enterprise-grade capabilities while the MCP and A2A patterns enable flexible, extensible architectures for future enhancements.
