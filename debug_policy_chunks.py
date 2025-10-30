#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.azure_services import AzureServiceManager
from app.core.config import settings

async def debug_policy_chunks():
    """Debug policy chunk retrieval to understand the issue"""
    
    print("🔍 Debugging policy chunk retrieval...")
    
    # Initialize Azure services
    azure_manager = AzureServiceManager()
    await azure_manager.initialize()
    
    # Get policy index name
    policy_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME
    print(f"📊 Using index: {policy_index}")
    
    # Get a document ID to test with
    documents = await azure_manager.list_unique_documents(policy_index)
    if not documents:
        print("❌ No documents found in policy index")
        return
    
    test_doc_id = documents[0].get('parent_id') or documents[0].get('document_id') or documents[0].get('id')
    print(f"🎯 Testing with document ID: {test_doc_id}")
    
    try:
        # Test direct chunk retrieval
        print("\n1️⃣ Testing direct get_chunks_for_document:")
        chunks = await azure_manager.get_chunks_for_document(policy_index, test_doc_id, top_k=10)
        print(f"   Direct method returned {len(chunks)} chunks")
        
        if chunks:
            first_chunk = chunks[0]
            print(f"   First chunk keys: {list(first_chunk.keys())}")
            print(f"   Content length: {len(first_chunk.get('content', ''))}")
        
        # Test manual search with client
        print("\n2️⃣ Testing manual search with client:")
        client = azure_manager.get_search_client_for_index(policy_index)
        
        # Try different filter expressions
        filter_expressions = [
            f"parent_id eq '{test_doc_id}'",
            f"document_id eq '{test_doc_id}'",
            f"id eq '{test_doc_id}'"
        ]
        
        for filter_expr in filter_expressions:
            print(f"   Testing filter: {filter_expr}")
            try:
                search_results = await client.search(
                    search_text="*",
                    filter=filter_expr,
                    top=5
                )
                
                results = [dict(r) async for r in search_results]
                print(f"     Found {len(results)} results")
                
                if results:
                    sample = results[0]
                    print(f"     Sample result keys: {list(sample.keys())}")
                    print(f"     Sample parent_id: {sample.get('parent_id')}")
                    print(f"     Sample document_id: {sample.get('document_id')}")
                    print(f"     Sample id: {sample.get('id')}")
                    break
                    
            except Exception as e:
                print(f"     Filter failed: {e}")
        
        # Test search without filter to see what's in the index
        print("\n3️⃣ Testing search without filter (first 3 results):")
        try:
            search_results = await client.search(
                search_text="*",
                top=3
            )
            
            results = [dict(r) async for r in search_results]
            print(f"   Found {len(results)} total results in index")
            
            for i, result in enumerate(results):
                print(f"   Result {i+1}:")
                print(f"     parent_id: {result.get('parent_id')}")
                print(f"     document_id: {result.get('document_id')}")
                print(f"     id: {result.get('id')}")
                print(f"     title: {result.get('title')}")
                print(f"     content length: {len(result.get('content', ''))}")
                print()
                
        except Exception as e:
            print(f"   Search without filter failed: {e}")
            
    except Exception as e:
        print(f"💥 Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(debug_policy_chunks())
    except KeyboardInterrupt:
        print("\n🛑 Debug interrupted by user")
    except Exception as e:
        print(f"💥 Debug failed with error: {e}")