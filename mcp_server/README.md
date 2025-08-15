# Financial RAG MCP Server

A Model Context Protocol (MCP) server for financial question answering using our RAG system with advanced multi-agent orchestration and insurance domain support.

## Overview

This MCP server implements the Model Context Protocol specification and provides comprehensive financial analysis capabilities through:

- **Multi-Agent Orchestration**: Coordinated processing using specialized agents
- **Insurance Domain Support**: Domain-specific agents for auto, life, health, dental, and general insurance
- **Streaming Responses**: Real-time progress updates for long-running operations
- **Multiple Protocols**: Support for stdio, HTTP, WebSocket, and Server-Sent Events (SSE)

## Features

### 🤖 Multi-Agent System
- **QA Agent**: Financial question answering with source verification
- **Document Processor**: Intelligent document analysis and extraction
- **Financial Analyzer**: Risk assessment and performance analysis
- **Insurance Agents**: Domain-specific insurance processing

### 🏥 Insurance Domain Support
- **Auto Insurance**: Vehicle collision, comprehensive, liability claims
- **Life Insurance**: Death benefit, disability, surrender claims
- **Health Insurance**: Medical treatment, prescription, preventive care
- **Dental Insurance**: Preventive, basic, major dental procedures
- **General Insurance**: Property, casualty, professional liability

### 📡 Streaming Capabilities
- **Real-time Progress**: Live updates during processing
- **Incremental Results**: Partial results as they become available
- **Multiple Protocols**: HTTP, WebSocket, and SSE support

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
cd agenticrag

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

#### Financial Analysis
```json
{
  "name": "answer_financial_question",
  "arguments": {
    "question": "What are the key risk factors for Microsoft?",
    "verification_level": "thorough",
    "use_multi_agent": true
  }
}
```

#### Document Search
```json
{
  "name": "search_financial_documents",
  "arguments": {
    "query": "quarterly earnings",
    "top_k": 10,
    "filters": {"document_type": ["10-K", "10-Q"]}
  }
}
```

#### Insurance Claim Processing
```json
{
  "name": "process_insurance_claim",
  "arguments": {
    "domain": "auto",
    "claim_type": "collision",
    "claim_data": {
      "vehicle_info": {...},
      "damage_details": {...},
      "witness_statements": [...]
    },
    "parallel_execution": true
  }
}
```

#### Insurance Policy Analysis
```json
{
  "name": "analyze_insurance_policy",
  "arguments": {
    "domain": "life",
    "policy_data": {
      "coverage_type": "term",
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
