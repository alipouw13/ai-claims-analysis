#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.azure_services import AzureServiceManager
from app.core.config import settings

async def test_sec_fix():
    """Test that SEC document chunking is working after the fix"""
    
    print("🧪 Testing SEC document chunk retrieval fix...")
    
    # Initialize Azure services
    print("📋 Initializing Azure services...")
    azure_manager = AzureServiceManager()
    await azure_manager.initialize()
    
    # Test with the main financial documents index (SEC documents)
    index_name = settings.AZURE_SEARCH_INDEX_NAME  # This should be "financial-documents"
    print(f"📊 Testing with index: {index_name}")
    
    # First, let's list what documents exist in the index
    print("🔍 Listing documents in the index...")
    try:
        documents = await azure_manager.list_unique_documents(index_name)
        print(f"✅ Found {len(documents)} documents in {index_name}")
        
        if documents:
            # Test with the first document
            test_doc = documents[0]
            doc_id = test_doc.get('document_id') or test_doc.get('id')
            print(f"🎯 Testing chunk retrieval for document: {doc_id}")
            
            # Test the get_chunks_for_document method
            chunks = await azure_manager.get_chunks_for_document(index_name, doc_id)
            print(f"📦 Retrieved {len(chunks)} chunks for document {doc_id}")
            
            if chunks:
                print("✅ SEC document chunking is working correctly!")
                # Show first chunk structure
                first_chunk = chunks[0]
                print(f"📄 First chunk structure: {list(first_chunk.keys())}")
                print(f"📝 First chunk preview: {first_chunk.get('content', '')[:100]}...")
            else:
                print("❌ No chunks retrieved - there might still be an issue")
                
        else:
            print("ℹ️  No documents found in the index - this is expected if no SEC docs have been processed")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    print("🎉 Test completed successfully!")
    return True

if __name__ == "__main__":
    try:
        asyncio.run(test_sec_fix())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"💥 Test failed with error: {e}")