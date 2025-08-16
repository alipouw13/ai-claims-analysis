# Risk Calculation Agent

## Overview

The **Risk Calculation Agent** is a specialized insurance agent that analyzes claim approval risk by comparing claim amounts against policy coverage limits. It provides automated decision-making for claim processing with clear recommendations for auto-approval or manual review.

## Key Features

### 🎯 **Core Functionality**
- **Claim Amount Extraction**: Automatically extracts claim amounts from various data fields
- **Policy Matching**: Uses vector search to find matching policies for claims
- **Risk Assessment**: Calculates risk scores based on coverage ratios
- **Decision Making**: Provides clear auto-approve or manual review recommendations

### 📊 **Risk Calculation Logic**

#### **Auto-Approve Scenarios**
1. **Low Risk (≤50% of coverage)**: Risk Score 10
   - Claim amount is 50% or less of policy coverage
   - Example: $5,000 claim on $100,000 policy

2. **Medium Risk (50-100% of coverage)**: Risk Score 30
   - Claim amount approaches but doesn't exceed coverage
   - Example: $80,000 claim on $100,000 policy

#### **Manual Review Required**
3. **High Risk (>100% of coverage)**: Risk Score 50-100
   - Claim amount exceeds policy coverage
   - Risk score scales with excess amount
   - Example: $120,000 claim on $100,000 policy

## Implementation Details

### **Agent Class: `RiskCalculationAgent`**

```python
class RiskCalculationAgent(InsuranceAgentBase):
    """Risk calculation agent for analyzing claim approval risk"""
    
    async def calculate_claim_risk(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk of approving a claim"""
```

### **Key Methods**

#### **1. Claim Amount Extraction**
```python
def _extract_claim_amount(self, claim_data: Dict[str, Any]) -> float:
    """Extract claim amount from claim data"""
```
- Searches multiple fields: `claim_amount`, `damage_estimate`, `settlement_amount`, etc.
- Handles both numeric and string formats
- Uses regex to extract numbers from text

#### **2. Policy Matching**
```python
async def _find_matching_policy(self, claim_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find matching policy using vector search"""
```
- Uses knowledge base or Azure Search tools
- Builds search queries from claim information
- Returns best matching policy document

#### **3. Risk Score Calculation**
```python
def _calculate_risk_score(self, claim_amount: float, policy_coverage: float) -> Dict[str, Any]:
    """Calculate risk score and decision"""
```

## Integration Points

### **Multi-Agent Orchestrator**
The Risk Calculation Agent is integrated into the `SemanticKernelInsuranceOrchestrator`:

```python
# Agent configuration
"risk_calculation": {
    "tools": ["azure_search", "knowledge_base", "code_interpreter", "file_search"],
    "indexes": ["claims-documents", "policy-documents"]
}
```

### **MCP Server Integration**
Added to the MCP server with new tool:

```json
{
    "name": "calculate_claim_risk",
    "description": "Calculate risk of approving an insurance claim based on policy coverage",
    "inputSchema": {
        "type": "object",
        "properties": {
            "claim_data": {
                "type": "object",
                "description": "Claim information including amount, policyholder, and policy number"
            },
            "policy_id": {
                "type": "string",
                "description": "Optional policy ID for direct matching"
            },
            "auto_approve_threshold": {
                "type": "number",
                "description": "Percentage of coverage below which claims are auto-approved",
                "default": 50
            }
        }
    }
}
```

## Usage Examples

### **Example 1: Auto-Approve Claim**
```python
claim_data = {
    "claim_id": "CL123456",
    "policyholder": "Emma Martinez",
    "policy_number": "PH789012",
    "claim_amount": 15000,
    "coverage_type": "Homeowners"
}

result = await risk_agent.calculate_claim_risk(claim_data)
# Result: auto_approve with risk_score: 10
```

### **Example 2: Manual Review Required**
```python
claim_data = {
    "claim_id": "CL789012",
    "policyholder": "John Smith",
    "policy_number": "PH456789",
    "claim_amount": 50000,
    "coverage_type": "Auto"
}

result = await risk_agent.calculate_claim_risk(claim_data)
# Result: manual_review_required with risk_score: 75
```

## API Endpoints

### **Risk Calculation Workflow**
```python
# Orchestrate risk calculation workflow
workflow_result = await orchestrator.orchestrate_workflow(
    workflow_type="risk_calculation",
    input_data={
        "claim_data": claim_data,
        "policy_id": policy_id,
        "auto_approve_threshold": 50
    }
)
```

### **Batch Risk Assessment**
```python
# Perform batch risk assessment for multiple claims
batch_result = await risk_plugin.batch_risk_assessment(claim_ids)
```

## Response Format

### **Successful Risk Calculation**
```json
{
    "domain": "risk_calculation",
    "risk_assessment": "auto_approve",
    "claim_amount": 15000.0,
    "policy_coverage": 455000.0,
    "policy_id": "POL789012",
    "risk_score": 10,
    "risk_factors": ["Claim within coverage limits"],
    "recommendation": "Auto-approve: Claim amount within policy coverage",
    "analysis_timestamp": "2024-01-15T10:30:00.000Z"
}
```

### **Manual Review Required**
```json
{
    "domain": "risk_calculation",
    "risk_assessment": "manual_review_required",
    "claim_amount": 50000.0,
    "policy_coverage": 25000.0,
    "policy_id": "POL456789",
    "risk_score": 75,
    "risk_factors": [
        "Claim amount ($50,000.00) exceeds policy coverage ($25,000.00)",
        "Excess amount: $25,000.00"
    ],
    "recommendation": "Manual review required: Claim exceeds policy coverage by $25,000.00",
    "analysis_timestamp": "2024-01-15T10:30:00.000Z"
}
```

## Testing

### **Test Script**
Run the test script to see the risk calculation logic in action:

```bash
python test/test_risk_calculation_agent.py
```

### **Test Scenarios**
1. **Low Risk**: $5,000 claim on $100,000 policy → Auto-approve
2. **Medium Risk**: $80,000 claim on $100,000 policy → Auto-approve with monitoring
3. **High Risk**: $120,000 claim on $100,000 policy → Manual review required

## Benefits

### **🚀 Automation**
- Reduces manual review workload for low-risk claims
- Provides consistent decision-making across all claims
- Speeds up claim processing for eligible cases

### **🎯 Risk Management**
- Clear risk scoring system
- Transparent decision criteria
- Audit trail for all risk assessments

### **📈 Scalability**
- Handles batch processing of multiple claims
- Integrates with existing insurance workflows
- Extensible for additional risk factors

### **🔍 Compliance**
- Maintains human oversight for high-risk claims
- Provides detailed reasoning for decisions
- Supports regulatory requirements

## Future Enhancements

### **Advanced Risk Factors**
- Claim history analysis
- Policyholder credit score
- Geographic risk factors
- Seasonal risk adjustments

### **Machine Learning Integration**
- Historical claim data training
- Predictive risk modeling
- Continuous learning from outcomes

### **Real-time Monitoring**
- Live risk score updates
- Alert system for threshold breaches
- Dashboard for risk analytics

## Conclusion

The Risk Calculation Agent provides a robust foundation for automated claim processing while maintaining appropriate human oversight for complex cases. It enhances the insurance workflow by providing clear, data-driven decisions that improve efficiency and consistency in claim handling.
