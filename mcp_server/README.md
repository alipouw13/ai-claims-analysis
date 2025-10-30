# AI Financial & Insurance Analysis Platform - MCP Server

A Model Context Protocol (MCP) server for the dual-domain Financial & Insurance Analysis Platform, providing comprehensive banking and insurance capabilities through advanced multi-agent orchestration.

## Overview

This MCP server implements the Model Context Protocol specification and provides comprehensive dual-domain analysis capabilities through:

- **Banking Domain**: SEC filings analysis, financial metrics extraction, company comparisons, investment risk assessment
- **Insurance Domain**: Claims processing, policy analysis, fraud detection, coverage validation
- **Multi-Agent Orchestration**: Coordinated processing using specialized domain agents
- **Cross-Domain Integration**: Seamless coordination between banking and insurance workflows
- **Streaming Responses**: Real-time progress updates for long-running operations
- **Multiple Protocols**: Support for stdio, HTTP, WebSocket, and Server-Sent Events (SSE)

## Features

### 🏦 Banking & Financial Analysis
- **SEC Document Analysis**: Comprehensive analysis of 10-K, 10-Q, 8-K filings
- **Financial Metrics Extraction**: AI-powered extraction of key performance indicators
- **Company Comparisons**: Multi-company financial performance analysis
- **Investment Risk Assessment**: Credit analysis and risk evaluation
- **Database Search**: Advanced financial document search and filtering

### 🏥 Insurance & Claims Processing
- **Claims Processing**: Automated claim analysis and assessment workflows
- **Policy Document Search**: Intelligent policy knowledge base queries
- **Coverage Validation**: Real-time policy coverage verification
- **Fraud Detection**: ML-powered fraud risk assessment
- **Document Analysis**: AI analysis of claim-related documents

### 🤖 Multi-Agent Orchestration
- **Domain-Specific Agents**: Specialized agents for banking and insurance workflows
- **Cross-Domain Coordination**: Seamless integration between banking and insurance processes
- **Workflow Management**: Intelligent task routing and execution
- **Real-time Processing**: Live progress updates and streaming responses

### 📡 Protocol Support
- **Multiple Interfaces**: HTTP, WebSocket, SSE, and stdio protocols
- **Claude Integration**: Native compatibility with Claude Desktop
- **VS Code Extensions**: Direct integration with development environments
- **Custom Clients**: Full MCP specification compliance for any client

## Installation

### Prerequisites
- Python 3.8+
- Azure OpenAI Service
- Azure AI Search
- Required environment variables (see Configuration)

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd ai-claims-analysis

# Install dependencies
pip install -r mcp_server/requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Azure credentials
```

## Configuration

### Environment Variables
```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=your-endpoint
AZURE_OPENAI_API_KEY=your-api-key

# Azure AI Search
AZURE_SEARCH_ENDPOINT=your-search-endpoint
AZURE_SEARCH_API_KEY=your-search-key

# Azure Authentication
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

### MCP Configuration
The server supports multiple configuration files:
- `.env.backend`: Backend service configuration
- `.env.mcp`: MCP-specific settings
- `mcp_config.json`: MCP server configuration

## Usage

### Command Line Interface

#### Stdio Mode (MCP Standard)
```bash
cd mcp_server
python main.py --mode stdio
```

#### HTTP Server Mode
```bash
cd mcp_server
python streaming_mcp_server.py --mode http --host 127.0.0.1 --port 8000
```

### Available Tools

#### Banking & Financial Analysis Tools

**analyze_financial_documents** - Comprehensive SEC filing and financial statement analysis
```json
{
  "name": "analyze_financial_documents",
  "arguments": {
    "document_ids": ["doc_123", "doc_456"],
    "analysis_type": "comprehensive"
  }
}
```

**search_financial_database** - Financial document search and investment research
```json
{
  "name": "search_financial_database",
  "arguments": {
    "query": "quarterly earnings technology sector",
    "filters": {"sector": "technology", "period": "Q3"},
    "limit": 10
  }
}
```

**extract_financial_metrics** - AI-powered extraction of key financial indicators
```json
{
  "name": "extract_financial_metrics",
  "arguments": {
    "document_id": "10k_aapl_2024",
    "metrics_type": "comprehensive"
  }
}
```

**compare_companies** - Multi-company financial comparison analysis
```json
{
  "name": "compare_companies",
  "arguments": {
    "company_a": "AAPL",
    "company_b": "MSFT",
    "metrics": ["revenue", "profit_margin", "debt_ratio"]
  }
}
```

**assess_investment_risk** - Financial risk analysis and creditworthiness evaluation
```json
{
  "name": "assess_investment_risk",
  "arguments": {
    "investment_data": {"symbol": "AAPL", "amount": 10000},
    "risk_factors": ["market_volatility", "sector_risk"]
  }
}
```

#### Insurance & Claims Tools

**process_insurance_claim** - Comprehensive claims analysis and assessment
```json
{
  "name": "process_insurance_claim",
  "arguments": {
    "claim_data": {
      "claim_type": "auto_collision",
      "policy_number": "POL123456",
      "damage_amount": 5000
    },
    "policy_id": "POL123456"
  }
}
```

**search_policy_documents** - Policy knowledge base search and coverage analysis
```json
{
  "name": "search_policy_documents",
  "arguments": {
    "query": "coverage limits comprehensive insurance",
    "policy_type": "auto",
    "limit": 5
  }
}
```

**analyze_claim_documents** - AI-powered analysis of submitted claim materials
```json
{
  "name": "analyze_claim_documents",
  "arguments": {
    "claim_id": "CLM789",
    "document_ids": ["doc_1", "doc_2", "doc_3"]
  }
}
```

**validate_coverage** - Policy coverage validation against claims
```json
{
  "name": "validate_coverage",
  "arguments": {
    "claim_data": {"damage_type": "collision", "amount": 3000},
    "policy_id": "POL123456"
  }
}
```

**assess_fraud_risk** - Fraud detection and risk assessment for claims
```json
{
  "name": "assess_fraud_risk",
  "arguments": {
    "claim_data": {"claim_amount": 15000, "incident_type": "theft"},
    "policy_history": {"claims_count": 2, "years_active": 5}
  }
}
```

#### Cross-Domain Tools

**coordinate_multi_domain_agents** - Multi-agent coordination across domains
```json
{
  "name": "coordinate_multi_domain_agents",
  "arguments": {
    "task_description": "Analyze financial exposure from insurance claims",
    "domains": ["banking", "insurance"]
  }
}
```

**get_system_statistics** - Processing metrics and system performance
```json
{
  "name": "get_system_statistics",
  "arguments": {
    "domains": ["banking", "insurance"]
  }
}
```
      "coverage_amount": 500000,
      "beneficiary_info": {...}
    },
    "analysis_type": "comprehensive"
  }
}
```

#### Agent Deployment
```json
{
  "name": "deploy_insurance_agent",
  "arguments": {
    "agent_name": "auto_claims_specialist",
    "agent_type": "auto",
    "tools": ["azure_search", "knowledge_base", "code_interpreter"],
    "instructions": "Specialize in auto insurance claim processing"
  }
}
```

### Available Resources

#### Financial Resources
- `financial://knowledge-base/statistics`: Knowledge base metrics
- `financial://agents/capabilities`: Agent capabilities
- `financial://documents/types`: Available document types
- `financial://system/status`: System health status

#### Insurance Resources
- `insurance://agents/status`: Insurance agent status
- `insurance://policies/types`: Policy type schemas
- `insurance://claims/types`: Claim processing workflows
- `insurance://orchestrator/status`: Orchestrator health

### Available Prompts

#### Financial Prompts
- `financial_analysis`: Comprehensive company analysis
- `risk_assessment`: Multi-company risk evaluation

#### Insurance Prompts
- `insurance_policy_analysis`: Policy coverage assessment
- `insurance_claim_processing`: Claim validation and processing

## API Endpoints

### HTTP Endpoints
- `POST /mcp/rpc`: Standard MCP JSON-RPC
- `POST /mcp/stream`: Streaming responses with SSE
- `POST /mcp/tools/call`: Direct tool invocation
- `GET /mcp/info`: Server information
- `GET /health`: Health check

### WebSocket Endpoints
- `WS /mcp/ws`: Bidirectional communication

## Streaming Support

### Server-Sent Events (SSE)
```javascript
const eventSource = new EventSource('/mcp/stream');
eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.step, data.message);
};
```

### WebSocket Streaming
```javascript
const ws = new WebSocket('ws://localhost:8000/mcp/ws');
ws.send(JSON.stringify({
  id: 'request-1',
  method: 'answer_financial_question',
  params: { question: 'What are the risks?' },
  stream: true
}));
```

## Insurance Agent Architecture

### Domain-Specific Agents
Each insurance domain has specialized agents:

#### Auto Insurance
- **Collision Agent**: Vehicle damage assessment
- **Liability Agent**: Third-party claims processing
- **Comprehensive Agent**: Non-collision damage

#### Life Insurance
- **Death Benefit Agent**: Death claim processing
- **Disability Agent**: Disability benefit assessment
- **Surrender Agent**: Policy surrender evaluation

#### Health Insurance
- **Medical Agent**: Treatment claim processing
- **Prescription Agent**: Drug claim validation
- **Preventive Agent**: Preventive care assessment

#### Dental Insurance
- **Preventive Agent**: Routine dental care
- **Basic Agent**: Basic procedure claims
- **Major Agent**: Major dental procedures

#### General Insurance
- **Property Agent**: Property damage claims
- **Casualty Agent**: Casualty claim processing
- **Professional Agent**: Professional liability

### Agent Orchestration
The system uses Semantic Kernel for advanced orchestration:

```python
# Agent coordination example
orchestrator = SemanticKernelInsuranceOrchestrator()
await orchestrator.coordinate_agents({
    "type": "complex_claim",
    "content": claim_data,
    "requirements": {"parallel": True, "verification": "thorough"}
})
```

## Development

### Adding New Insurance Agents
1. Define agent capabilities in `insurance_agents.py`
2. Add agent type to the orchestrator
3. Update MCP tools and resources
4. Add streaming support if needed

### Testing
```bash
# Test stdio mode
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | python main.py

# Test HTTP mode
curl -X POST http://localhost:8000/mcp/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

### Debugging
```bash
# Enable debug logging
python streaming_mcp_server.py --mode http --debug

# Check server status
curl http://localhost:8000/health
```

## Troubleshooting

### Common Issues

#### Import Errors
- Ensure all dependencies are installed
- Check Python path includes backend directory
- Verify environment variables are set

#### Azure Connection Issues
- Validate Azure credentials
- Check network connectivity
- Verify service endpoints

#### Agent Initialization Failures
- Check agent configuration
- Verify Semantic Kernel setup
- Review orchestrator logs

### Logging
The server provides detailed logging at multiple levels:
- **ERROR**: Critical failures and exceptions
- **INFO**: General operation information
- **DEBUG**: Detailed debugging information

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review the logs for error details
- Open an issue on GitHub
- Contact the development team
