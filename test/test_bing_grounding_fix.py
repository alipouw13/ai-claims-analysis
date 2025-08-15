#!/usr/bin/env python3
"""
Test script to verify that the BingGroundingTool import works.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_bing_grounding_import():
    """Test that BingGroundingTool can be imported correctly"""
    try:
        from azure.ai.agents.models import BingGroundingTool
        print(" BingGroundingTool import successful from azure.ai.agents.models")
        return True
    except ImportError as e:
        print(f" BingGroundingTool import failed: {e}")
        return False

def test_azure_ai_agent_service_import():
    """Test that the Azure AI Agent Service can be imported without warnings"""
    try:
        # This should not raise any import errors related to BingGroundingTool
        from app.services.agents.azure_ai_agent_service import AzureAIAgentService
        print(" AzureAIAgentService import successful")
        return True
    except ImportError as e:
        print(f"AzureAIAgentService import failed: {e}")
        return False

def test_available_tools():
    """Test what tools are available in the Azure AI Agents package"""
    try:
        from azure.ai.agents.models import (
            BingGroundingTool,
            CodeInterpreterTool,
            FileSearchTool,
            AzureAISearchTool
        )
        print(" All expected tools are available:")
        print(f"  - BingGroundingTool: {BingGroundingTool}")
        print(f"  - CodeInterpreterTool: {CodeInterpreterTool}")
        print(f"  - FileSearchTool: {FileSearchTool}")
        print(f"  - AzureAISearchTool: {AzureAISearchTool}")
        return True
    except ImportError as e:
        print(f" Tool import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing BingGroundingTool import fix...")
    print("=" * 50)
    
    success = True
    
    # Test 1: Direct import
    if not test_bing_grounding_import():
        success = False
    
    # Test 2: Service import
    if not test_azure_ai_agent_service_import():
        success = False
    
    # Test 3: Available tools
    if not test_available_tools():
        success = False
    
    print("=" * 50)
    if success:
        print("✅ All tests passed! BingGroundingTool import issue is resolved.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return success

if __name__ == "__main__":
    main()
