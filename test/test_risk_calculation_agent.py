#!/usr/bin/env python3
"""
Test script for Risk Calculation Agent

This script demonstrates the new Risk Calculation Agent functionality
for analyzing claim approval risk based on policy coverage.
"""

import asyncio
import json
from typing import Dict, Any

# Mock data for testing
SAMPLE_CLAIM_DATA = {
    "claim_id": "CL123456",
    "policyholder": "Emma Martinez",
    "policy_number": "PH789012",
    "coverage_type": "Homeowners",
    "claim_amount": 15000,
    "damage_estimate": 15000,
    "date_of_loss": "2021-07-25",
    "description": "Tree fell on roof during storm, causing structural damage"
}

SAMPLE_POLICY_DATA = {
    "id": "POL789012",
    "policyholder": "Emma Martinez",
    "policy_number": "PH789012",
    "coverage_type": "Homeowners",
    "coverage": {
        "dwelling": 250000,
        "personal_property": 100000,
        "liability": 300000,
        "medical_payments": 5000
    }
}

SAMPLE_CLAIM_OVER_LIMIT = {
    "claim_id": "CL789012",
    "policyholder": "John Smith",
    "policy_number": "PH456789",
    "coverage_type": "Auto",
    "claim_amount": 50000,
    "damage_estimate": 50000,
    "date_of_loss": "2021-08-15",
    "description": "Major collision with multiple vehicle damage"
}

SAMPLE_POLICY_LOW_LIMIT = {
    "id": "POL456789",
    "policyholder": "John Smith",
    "policy_number": "PH456789",
    "coverage_type": "Auto",
    "coverage": {
        "liability": 25000,
        "collision": 25000,
        "comprehensive": 25000
    }
}

async def test_risk_calculation_agent():
    """Test the Risk Calculation Agent with sample data"""
    
    print("🧪 Testing Risk Calculation Agent")
    print("=" * 50)
    
    # Import the agent (this would normally be done through the orchestrator)
    try:
        from app.services.agents.insurance_agents import RiskCalculationAgent
        from app.services.agent_tools import AzureSearchTool, KnowledgeBaseTool
        
        # Create mock tools
        mock_tools = [
            AzureSearchTool(),  # Mock tool
            KnowledgeBaseTool()  # Mock tool
        ]
        
        # Create risk calculation agent
        agent = RiskCalculationAgent(mock_tools)
        await agent.initialize()
        
        print("✅ Risk Calculation Agent initialized successfully")
        
        # Test 1: Claim within policy limits (should auto-approve)
        print("\n📋 Test 1: Claim within policy limits")
        print("-" * 30)
        
        # Mock the policy search result
        agent._find_matching_policy = lambda claim_data: asyncio.create_task(
            asyncio.Future().set_result(SAMPLE_POLICY_DATA)
        )
        
        result1 = await agent.calculate_claim_risk(SAMPLE_CLAIM_DATA)
        print(f"Claim Amount: ${SAMPLE_CLAIM_DATA['claim_amount']:,}")
        print(f"Policy Coverage: ${sum(SAMPLE_POLICY_DATA['coverage'].values()):,}")
        print(f"Risk Assessment: {result1.get('risk_assessment', 'Unknown')}")
        print(f"Risk Score: {result1.get('risk_score', 'Unknown')}")
        print(f"Recommendation: {result1.get('recommendation', 'Unknown')}")
        
        # Test 2: Claim exceeds policy limits (should require manual review)
        print("\n📋 Test 2: Claim exceeds policy limits")
        print("-" * 30)
        
        # Mock the policy search result
        agent._find_matching_policy = lambda claim_data: asyncio.create_task(
            asyncio.Future().set_result(SAMPLE_POLICY_LOW_LIMIT)
        )
        
        result2 = await agent.calculate_claim_risk(SAMPLE_CLAIM_OVER_LIMIT)
        print(f"Claim Amount: ${SAMPLE_CLAIM_OVER_LIMIT['claim_amount']:,}")
        print(f"Policy Coverage: ${sum(SAMPLE_POLICY_LOW_LIMIT['coverage'].values()):,}")
        print(f"Risk Assessment: {result2.get('risk_assessment', 'Unknown')}")
        print(f"Risk Score: {result2.get('risk_score', 'Unknown')}")
        print(f"Recommendation: {result2.get('recommendation', 'Unknown')}")
        
        # Test 3: Claim amount extraction
        print("\n📋 Test 3: Claim amount extraction")
        print("-" * 30)
        
        test_claim_data = {
            "claim_amount": "25,000",
            "damage_estimate": "30,000",
            "estimated_loss": 15000
        }
        
        extracted_amount = agent._extract_claim_amount(test_claim_data)
        print(f"Extracted claim amount: ${extracted_amount:,.2f}")
        
        # Test 4: Policy coverage extraction
        print("\n📋 Test 4: Policy coverage extraction")
        print("-" * 30)
        
        extracted_coverage = agent._extract_policy_coverage(SAMPLE_POLICY_DATA)
        print(f"Extracted policy coverage: ${extracted_coverage:,.2f}")
        
        print("\n✅ All tests completed successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the correct directory")
    except Exception as e:
        print(f"❌ Test failed: {e}")

def demonstrate_risk_logic():
    """Demonstrate the risk calculation logic"""
    
    print("\n🔍 Risk Calculation Logic Demonstration")
    print("=" * 50)
    
    # Example scenarios
    scenarios = [
        {
            "name": "Low Risk - Well within limits",
            "claim_amount": 5000,
            "policy_coverage": 100000,
            "expected_decision": "auto_approve"
        },
        {
            "name": "Medium Risk - Approaching limit",
            "claim_amount": 80000,
            "policy_coverage": 100000,
            "expected_decision": "auto_approve"
        },
        {
            "name": "High Risk - Exceeds limit",
            "claim_amount": 120000,
            "policy_coverage": 100000,
            "expected_decision": "manual_review_required"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📊 {scenario['name']}")
        print(f"   Claim Amount: ${scenario['claim_amount']:,}")
        print(f"   Policy Coverage: ${scenario['policy_coverage']:,}")
        print(f"   Coverage Ratio: {scenario['claim_amount'] / scenario['policy_coverage']:.1%}")
        print(f"   Expected Decision: {scenario['expected_decision']}")
        
        if scenario['claim_amount'] <= scenario['policy_coverage']:
            if scenario['claim_amount'] / scenario['policy_coverage'] <= 0.5:
                print("   ✅ Auto-approve: Claim is 50% or less of coverage")
            else:
                print("   ⚠️  Auto-approve with monitoring: Claim approaching limit")
        else:
            excess = scenario['claim_amount'] - scenario['policy_coverage']
            print(f"   ❌ Manual review required: Exceeds coverage by ${excess:,}")

if __name__ == "__main__":
    print("🚀 Risk Calculation Agent Test Suite")
    print("=" * 60)
    
    # Demonstrate the logic first
    demonstrate_risk_logic()
    
    # Run the async tests
    try:
        asyncio.run(test_risk_calculation_agent())
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        print("This is expected if the full application environment is not set up")
        print("The risk calculation logic demonstration above shows the core functionality")
