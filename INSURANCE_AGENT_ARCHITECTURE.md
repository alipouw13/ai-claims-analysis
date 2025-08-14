# Insurance Agent Architecture with Semantic Kernel Orchestration

## Overview

This document describes the new insurance agent architecture that implements domain-specific agents with Semantic Kernel orchestration for insurance workflows. The system supports parallel agent execution and provides specialized tools for different insurance domains.

## Architecture Components

### 1. **Agent Tools** (`app/services/agent-tools/`)

#### Core Tools Available:
- **Azure Search Tool** (`azure_search_tool.py`)
  - Hybrid search across multiple indexes
  - Vector and keyword search capabilities
  - Domain-specific index routing (claims vs policies)

- **Bing Search Tool** (`bing_search_tool.py`)
  - Web grounding and fact verification
  - Current information retrieval
  - News and market data access

- **Knowledge Base Tool** (`knowledge_base_tool.py`)
  - Policy and claims management
  - Document operations and analytics
  - Knowledge base operations

- **Code Interpreter Tool** (`code_interpreter_tool.py`)
  - Python code execution for calculations
  - Insurance data analysis
  - Report generation and metrics calculation

- **File Search Tool** (`file_search_tool.py`)
  - File search and retrieval
  - Document content analysis
  - Insurance document management

### 2. **Domain-Specific Insurance Agents** (`app/services/agents/insurance_agents.py`)

#### Available Agents:

##### **Auto Insurance Agent**
- **Capabilities**: Auto policy analysis, vehicle claims processing, accident assessment, coverage verification, liability analysis, damage evaluation
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search
- **Indexes**: claims-documents, policy-documents

##### **Life Insurance Agent**
- **Capabilities**: Life policy analysis, beneficiary verification, death claim processing, underwriting assessment, policy valuation
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search
- **Indexes**: policy-documents

##### **Health Insurance Agent**
- **Capabilities**: Health policy analysis, medical claims processing, preauthorization review, benefit verification, network analysis
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search
- **Indexes**: claims-documents, policy-documents

##### **Dental Insurance Agent**
- **Capabilities**: Dental policy analysis, dental claims processing, treatment plan review, benefit verification, network analysis
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search
- **Indexes**: claims-documents, policy-documents

##### **General Insurance Agent** (Fallback)
- **Capabilities**: General policy analysis, general claims processing, risk assessment, coverage analysis
- **Tools**: Azure Search, Knowledge Base, Code Interpreter, File Search, Bing Search
- **Indexes**: claims-documents, policy-documents

### 3. **Semantic Kernel Orchestrator** (`app/services/agents/semantic_kernel_insurance_orchestrator.py`)

#### Features:
- **Parallel Agent Execution**: Multiple agents can work simultaneously
- **Custom Orchestration Logic**: Similar to SEC financial multi-agent orchestrator
- **Domain-Specific Routing**: Automatic routing to appropriate agents
- **Semantic Kernel Integration**: Uses Microsoft's Semantic Kernel for planning and execution
- **Plugin Architecture**: Custom plugins for insurance workflows

#### Orchestration Workflows:
1. **Policy Analysis Workflow**
   - Route to domain-specific agent
   - Analyze policy coverage and risks
   - Generate recommendations

2. **Claims Processing Workflow**
   - Validate claim data
   - Assess damage and liability
   - Calculate settlement amounts

3. **Customer Support Workflow**
   - Answer insurance questions
   - Provide policy information
   - Assist with claims

### 4. **API Endpoints** (`app/api/routes/insurance_orchestration.py`)

#### Available Endpoints:

##### **Orchestration Endpoints**
- `POST /api/v1/insurance/orchestrate/policy-analysis`
- `POST /api/v1/insurance/orchestrate/claims-processing`
- `POST /api/v1/insurance/orchestrate/customer-support`

##### **Agent-Specific Endpoints**
- `POST /api/v1/insurance/agents/{domain}/analyze-policy`
- `POST /api/v1/insurance/agents/{domain}/process-claim`

##### **Status and Information Endpoints**
- `GET /api/v1/insurance/orchestrator/status`
- `GET /api/v1/insurance/agents/available`
- `GET /api/v1/insurance/tools/available`

## Usage Examples

### 1. **Policy Analysis Workflow**

```python
# Analyze auto insurance policy
response = await client.post("/api/v1/insurance/orchestrate/policy-analysis", json={
    "domain": "auto",
    "policy_data": {
        "coverage": {
            "liability": {"limit": 50000},
            "collision": {"deductible": 500},
            "comprehensive": {"deductible": 500}
        },
        "vehicle": {
            "make_model": "Toyota Camry",
            "year": 2020,
            "value": 25000
        },
        "driver": {
            "age": 30,
            "accidents": 0,
            "violations": 0
        }
    },
    "parallel_execution": True
})
```

### 2. **Claims Processing Workflow**

```python
# Process auto insurance claim
response = await client.post("/api/v1/insurance/orchestrate/claims-processing", json={
    "domain": "auto",
    "claim_data": {
        "date_of_loss": "2024-01-15T10:30:00Z",
        "description": "Rear-end collision",
        "damage_estimate": 5000,
        "deductible": 500,
        "accident_details": {
            "speeding": False,
            "failure_to_yield": False,
            "following_too_closely": True
        }
    },
    "parallel_execution": True
})
```

### 3. **Customer Support Workflow**

```python
# Customer support inquiry
response = await client.post("/api/v1/insurance/orchestrate/customer-support", json={
    "question": "What does my auto insurance policy cover?",
    "domain": "auto",
    "parallel_execution": True
})
```

## Configuration

### Environment Variables Required:

```bash
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

# Bing Search (optional)
BING_SEARCH_SUBSCRIPTION_KEY=your_bing_key
BING_SEARCH_ENDPOINT=your_bing_endpoint

# Azure Authentication
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
```

## Agent Tool Access Control

### Domain-Specific Tool Access:

| Agent Domain | Azure Search | Knowledge Base | Code Interpreter | File Search | Bing Search |
|--------------|--------------|----------------|------------------|-------------|-------------|
| Auto         | ✅           | ✅             | ✅               | ✅          | ❌          |
| Life         | ✅           | ✅             | ✅               | ✅          | ❌          |
| Health       | ✅           | ✅             | ✅               | ✅          | ❌          |
| Dental       | ✅           | ✅             | ✅               | ✅          | ❌          |
| General      | ✅           | ✅             | ✅               | ✅          | ✅          |

### Index Access by Domain:

| Agent Domain | Policy Index | Claims Index |
|--------------|--------------|--------------|
| Auto         | ✅           | ✅           |
| Life         | ✅           | ❌           |
| Health       | ✅           | ✅           |
| Dental       | ✅           | ✅           |
| General      | ✅           | ✅           |

## Parallel Execution Strategy

### Workflow Types:

1. **Sequential Execution**
   - Uses Semantic Kernel planner
   - Step-by-step workflow execution
   - Good for complex, dependent tasks

2. **Parallel Execution**
   - Multiple agents work simultaneously
   - Faster execution for independent tasks
   - Automatic result aggregation

### Agent Coordination:

- **Primary Agent**: Domain-specific agent handles main task
- **Fallback Agent**: General agent provides additional insights
- **Tool Coordination**: Agents share tools but work independently
- **Result Aggregation**: Orchestrator combines results from all agents

## Error Handling and Fallbacks

### Error Handling Strategy:

1. **Agent-Level Errors**: Individual agent failures don't stop workflow
2. **Tool-Level Errors**: Graceful degradation when tools are unavailable
3. **Domain Fallback**: General agent handles unsupported domains
4. **Tool Fallback**: Alternative tools when primary tools fail

### Monitoring and Observability:

- Request tracking and metrics
- Error logging and alerting
- Performance monitoring
- Agent and tool status monitoring

## Future Enhancements

### Planned Features:

1. **Durable Functions Integration**
   - Long-running workflows
   - State management
   - Retry logic

2. **Advanced Orchestration**
   - Dynamic agent selection
   - Workflow optimization
   - Load balancing

3. **Enhanced Tools**
   - Document processing tools
   - Image analysis tools
   - Voice processing tools

4. **Azure AI Foundry Integration**
   - Native agent deployment
   - Tool marketplace integration
   - Advanced orchestration capabilities

## Troubleshooting

### Common Issues:

1. **Semantic Kernel Not Available**
   - Install semantic-kernel package
   - Check Python environment

2. **Agent Initialization Failures**
   - Verify environment variables
   - Check Azure service connectivity
   - Review tool initialization logs

3. **Parallel Execution Issues**
   - Check agent availability
   - Verify tool access permissions
   - Review orchestration logs

### Debug Endpoints:

- `GET /api/v1/insurance/orchestrator/status` - Check orchestrator health
- `GET /api/v1/insurance/agents/available` - List available agents
- `GET /api/v1/insurance/tools/available` - List available tools

## Conclusion

This insurance agent architecture provides a robust, scalable solution for insurance workflows with domain-specific expertise and parallel execution capabilities. The Semantic Kernel integration enables intelligent orchestration while maintaining flexibility for future enhancements.
