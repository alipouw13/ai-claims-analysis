# Azure AI Foundry Evaluations Setup Guide

## Overview

This guide explains how to configure and use Azure AI Foundry evaluations instead of just local evaluations in your AI Claims Analysis application.

## Architecture

### Evaluation Types Available

1. **Custom Evaluations** (existing)
   - Local evaluators using your OpenAI models
   - Custom financial accuracy evaluators
   - Citation quality evaluators

2. **Azure AI Foundry Evaluations** (new)
   - Built-in Azure evaluators with enterprise-grade reliability
   - Groundedness, Relevance, Coherence, Fluency
   - Agent-specific evaluators for multi-agent scenarios

3. **Hybrid Evaluations**
   - Combination of both custom and Azure AI Foundry evaluators
   - Best of both worlds approach

## Configuration

### 1. Environment Variables (.env file)

```bash
# Enable telemetry and monitoring
ENABLE_TELEMETRY=true
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
AZURE_AI_FOUNDRY_TRACING_ENABLED=true

# Azure AI Foundry Evaluation Configuration
AZURE_AI_FOUNDRY_EVALUATION_ENABLED=true
EVALUATION_FRAMEWORK_TYPE=azure_ai_foundry  # or "hybrid" or "custom"
AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING=https://insurance-resource.services.ai.azure.com/api/projects/insurance
AZURE_AI_FOUNDRY_EVALUATOR_MODEL=gpt-4.1-mini

# Existing evaluation settings
EVALUATION_ENABLED=true
EVALUATION_MODEL=gpt-4.1-mini
```

### 2. Framework Types

Choose your evaluation strategy:

- `EVALUATION_FRAMEWORK_TYPE=custom` - Use only local evaluators
- `EVALUATION_FRAMEWORK_TYPE=azure_ai_foundry` - Use only Azure AI Foundry evaluators  
- `EVALUATION_FRAMEWORK_TYPE=hybrid` - Use both (recommended)

## Usage

### 1. Standard Q&A with Automatic Evaluation

When you make Q&A requests through your existing endpoints, evaluations now run automatically if enabled:

**Banking Q&A:**
```bash
POST /api/v1/qa/ask
{
  "question": "What was the company's revenue in Q3?",
  "session_id": "session_123"
}
```

**Insurance Q&A:**
```bash
POST /api/v1/qa/insurance/ask
{
  "question": "What is covered under this policy?",
  "session_id": "session_456"
}
```

### 2. Explicit Azure AI Foundry Evaluation

Use the dedicated Foundry evaluation endpoint:

```bash
POST /api/v1/evaluation/evaluate/foundry
{
  "question_id": "q_123",
  "session_id": "session_123",
  "question": "What was the company's revenue?",
  "answer": "The company's Q3 revenue was $2.5M according to the 10-K filing.",
  "context": [
    {
      "content": "Q3 revenue: $2.5 million",
      "source": "10-K Filing",
      "page_number": 15
    }
  ],
  "ground_truth": "Company Q3 revenue was $2.5M",
  "evaluation_model": "gpt-4.1-mini"
}
```

### 3. Check Foundry Status

Verify Azure AI Foundry evaluation is configured correctly:

```bash
GET /api/v1/evaluation/foundry/status
```

Response:
```json
{
  "status": "available",
  "framework_type": "azure_ai_foundry",
  "azure_ai_foundry_configured": true,
  "available_evaluators": [
    "groundedness",
    "relevance", 
    "coherence",
    "fluency",
    "retrieval"
  ],
  "agent_evaluators": [
    "intent_resolution",
    "tool_call_accuracy", 
    "task_adherence"
  ]
}
```

## Evaluation Results

### Azure AI Foundry Metrics

**Core RAG Evaluators:**
- **Groundedness** (0.0-1.0): How well the response is supported by the provided context
- **Relevance** (0.0-1.0): How relevant the response is to the user's question  
- **Coherence** (0.0-1.0): How logically consistent and well-structured the response is
- **Fluency** (0.0-1.0): How natural and readable the response is
- **Retrieval** (0.0-1.0): How accurate the document retrieval was

**Agent-Specific Evaluators:**
- **Intent Resolution** (0.0-1.0): How well the agent understood and addressed the user's intent
- **Tool Call Accuracy** (0.0-1.0): How accurately the agent used available tools
- **Task Adherence** (0.0-1.0): How well the agent followed the given task instructions

### Custom Financial Evaluators

- **Financial Accuracy** (0.0-1.0): Accuracy of financial figures and terminology
- **Citation Quality** (0.0-1.0): Quality and accuracy of source citations
- **Response Time** (0.0-1.0): Speed of response generation

## Monitoring and Observability

### Azure AI Foundry Portal

With Azure AI Foundry evaluations enabled, you can monitor:

1. **Evaluation Traces** - View detailed evaluation runs in the Azure AI Foundry portal
2. **Performance Metrics** - Track evaluation scores over time
3. **Cost Analysis** - Monitor evaluation costs and token usage
4. **Model Comparisons** - Compare different model performance

### Application Insights

Monitor evaluation metrics through your Application Insights dashboard:

- Evaluation request volume
- Average evaluation scores by type
- Evaluation latency and errors
- Token usage for evaluations

### API Endpoints for Analytics

```bash
# Get evaluation analytics
GET /api/v1/evaluation/analytics?days=7&evaluator_type=foundry

# Get session-specific results  
GET /api/v1/evaluation/results/session/{session_id}

# Get evaluation summaries
GET /api/v1/evaluation/summary/session/{session_id}
```

## Benefits of Azure AI Foundry Evaluations

### 1. **Enterprise Reliability**
- Microsoft-managed evaluation infrastructure
- Consistent scoring across Azure regions
- Built-in redundancy and failover

### 2. **Advanced Metrics**
- Research-backed evaluation methodologies
- Continuous improvement from Microsoft Research
- Industry-standard benchmarking

### 3. **Integration Benefits**
- Native Azure AI Foundry portal integration
- Automated experiment tracking
- Built-in A/B testing capabilities

### 4. **Cost Efficiency**
- Optimized evaluation models
- Reduced latency vs custom evaluations
- Shared infrastructure costs

## Troubleshooting

### Common Issues

1. **Foundry Not Available**
   ```
   "azure_ai_foundry_configured": false
   ```
   - Check `AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING` is set
   - Verify Azure AI Foundry project is accessible
   - Ensure proper Azure credentials are configured

2. **Evaluation Failures**
   - Check Application Insights logs for detailed errors
   - Verify Azure OpenAI model deployments are available
   - Check network connectivity to Azure services

3. **Mixed Results**
   - In hybrid mode, some evaluations may succeed while others fail
   - Check individual evaluation results for specific errors
   - Consider falling back to custom-only mode if needed

### Logs and Debugging

Enable detailed logging:
```bash
LOG_LEVEL=DEBUG
ENABLE_DEBUG_LOGGING=true
```

Monitor evaluation logs:
```bash
# Check application logs
docker logs ai-claims-analysis-backend

# Check Azure AI Foundry tracing
# View traces in Azure AI Foundry portal under "Tracing" section
```

## Migration Strategy

### Phase 1: Enable Monitoring
```bash
ENABLE_TELEMETRY=true
EVALUATION_FRAMEWORK_TYPE=custom  # Keep existing
```

### Phase 2: Hybrid Testing  
```bash
EVALUATION_FRAMEWORK_TYPE=hybrid  # Test both side by side
```

### Phase 3: Full Migration
```bash
EVALUATION_FRAMEWORK_TYPE=azure_ai_foundry  # Azure Foundry only
```

This phased approach allows you to:
1. Verify monitoring works correctly
2. Compare Azure Foundry vs custom evaluation results
3. Gradually migrate to full Foundry-based evaluations

## Next Steps

1. **Configure Environment Variables** - Update your .env file with Foundry settings
2. **Restart Application** - Apply the new configuration
3. **Test Foundry Status** - Use `/api/v1/evaluation/foundry/status` endpoint
4. **Run Test Evaluations** - Try the new `/api/v1/evaluation/evaluate/foundry` endpoint
5. **Monitor Results** - Check Azure AI Foundry portal for traces and metrics