#!/usr/bin/env python3
"""
Script to check Azure configuration and identify any issues.
"""

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings

def check_azure_config():
    """Check Azure configuration and report any issues"""
    
    print("🔍 Checking Azure Configuration...")
    print("=" * 50)
    
    # Check required environment variables
    required_vars = [
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID", 
        "AZURE_CLIENT_ID",
        "AZURE_SEARCH_SERVICE_NAME",
        "AZURE_SEARCH_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_COSMOS_ENDPOINT"
    ]
    
    # Optional environment variables
    optional_vars = [
        "AZURE_FORM_RECOGNIZER_ENDPOINT"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = getattr(settings, var, None)
        if not value:
            missing_vars.append(var)
            print(f"❌ Missing: {var}")
        else:
            # Mask sensitive values
            if "SECRET" in var or "KEY" in var:
                masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "***"
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
    
    # Check optional variables
    print("\nOptional Environment Variables:")
    for var in optional_vars:
        value = getattr(settings, var, None)
        if not value:
            print(f"⚠️  Optional: {var} (not set)")
        else:
            print(f"✅ {var}: {value}")
    
    print("\n" + "=" * 50)
    
    if missing_vars:
        print(f"❌ Found {len(missing_vars)} missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables in your .env file")
        return False
    else:
        print("✅ All required Azure environment variables are set!")
        return True

def check_azure_search_indexes():
    """Check if Azure Search indexes are accessible"""
    print("\n🔍 Checking Azure Search Indexes...")
    print("=" * 50)
    
    try:
        from azure.search.documents.indexes import SearchIndexClient
        from azure.core.credentials import AzureKeyCredential
        
        endpoint = f"https://{settings.AZURE_SEARCH_SERVICE_NAME}.search.windows.net"
        credential = AzureKeyCredential(settings.AZURE_SEARCH_API_KEY)
        client = SearchIndexClient(endpoint=endpoint, credential=credential)
        
        # List all indexes
        indexes = list(client.list_indexes())
        index_names = [idx.name for idx in indexes]
        
        print(f"✅ Connected to Azure Search service: {settings.AZURE_SEARCH_SERVICE_NAME}")
        print(f"✅ Found {len(indexes)} indexes:")
        
        expected_indexes = [
            settings.AZURE_SEARCH_INDEX_NAME,
            settings.AZURE_SEARCH_POLICY_INDEX_NAME,
            settings.AZURE_SEARCH_CLAIMS_INDEX_NAME
        ]
        
        for expected in expected_indexes:
            if expected in index_names:
                print(f"   ✅ {expected}")
            else:
                print(f"   ❌ {expected} (missing)")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to Azure Search: {e}")
        return False

def check_azure_openai():
    """Check if Azure OpenAI is accessible"""
    print("\n🔍 Checking Azure OpenAI...")
    print("=" * 50)
    
    try:
        from openai import AsyncAzureOpenAI
        
        client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION
        )
        
        # Try to list models (this will test the connection)
        import asyncio
        async def test_connection():
            models = await client.models.list()
            return [model.id for model in models.data]
        
        model_names = asyncio.run(test_connection())
        
        print(f"✅ Connected to Azure OpenAI: {settings.AZURE_OPENAI_ENDPOINT}")
        print(f"✅ Found {len(model_names)} models")
        
        # Check for expected deployments
        expected_deployments = [
            settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
        ]
        
        for deployment in expected_deployments:
            if deployment in model_names:
                print(f"   ✅ {deployment}")
            else:
                print(f"   ❌ {deployment} (missing)")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to Azure OpenAI: {e}")
        return False

def main():
    """Main function to run all checks"""
    print("🚀 Azure Configuration Checker")
    print("=" * 50)
    
    # Check environment variables
    env_ok = check_azure_config()
    
    if env_ok:
        # Check Azure Search
        search_ok = check_azure_search_indexes()
        
        # Check Azure OpenAI
        openai_ok = check_azure_openai()
        
        print("\n" + "=" * 50)
        print("📊 Summary:")
        print(f"   Environment Variables: {'✅' if env_ok else '❌'}")
        print(f"   Azure Search: {'✅' if search_ok else '❌'}")
        print(f"   Azure OpenAI: {'✅' if openai_ok else '❌'}")
        
        if env_ok and search_ok and openai_ok:
            print("\n🎉 All Azure services are properly configured!")
            print("The application should work correctly.")
        else:
            print("\n⚠️ Some Azure services have issues.")
            print("Please fix the issues above before running the application.")
    else:
        print("\n❌ Environment variables are missing.")
        print("Please set the required environment variables before running the application.")

if __name__ == "__main__":
    main()
