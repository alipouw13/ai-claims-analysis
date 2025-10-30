#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.azure_services import AzureServiceManager
from app.core.config import settings

async def debug_sec_index():
    """Debug the SEC index structure to understand the filtering issue"""
    
    print("🔍 Debugging SEC index structure...")
    
    # Initialize Azure services
    azure_manager = AzureServiceManager()
    await azure_manager.initialize()
    
    index_name = "rag-sec"  # Based on the test output
    print(f"📊 Debugging index: {index_name}")
    
    # Get the search client
    client = azure_manager.get_search_client_for_index(index_name)
    
    # Get a few sample documents without any filters
    print("📦 Getting sample documents from index...")
    try:
        results = await client.search(
            search_text="*",
            top=5
        )
        
        documents = []
        async for result in results:
            documents.append(dict(result))
            
        print(f"📄 Found {len(documents)} sample documents")
        
        if documents:
            # Examine the structure of the first document
            first_doc = documents[0]
            print(f"\n🔍 First document structure:")
            for key, value in first_doc.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: '{value[:100]}...' (length: {len(value)})")
                else:
                    print(f"  {key}: {value}")
            
            # Look for document_id field specifically
            if 'document_id' in first_doc:
                doc_id = first_doc['document_id']
                print(f"\n🎯 Testing filter with document_id: {doc_id}")
                
                # Test the exact filter we're using
                filter_expr = f"document_id eq '{doc_id}'"
                print(f"🔍 Filter expression: {filter_expr}")
                
                filtered_results = await client.search(
                    search_text="*",
                    filter=filter_expr,
                    top=10
                )
                
                filtered_docs = []
                async for result in filtered_results:
                    filtered_docs.append(dict(result))
                
                print(f"📦 Filter returned {len(filtered_docs)} documents")
                
                if filtered_docs:
                    print("✅ Filter is working!")
                    # Show the first filtered document
                    filtered_doc = filtered_docs[0]
                    print(f"📄 Filtered document keys: {list(filtered_doc.keys())}")
                else:
                    print("❌ Filter returned no results!")
                    
                    # Try a broader search to see what document_id values exist
                    print("\n🔍 Searching for any documents with this pattern...")
                    partial_search = await client.search(
                        search_text="*",
                        filter=f"search.ismatch('{doc_id[:10]}*', 'document_id')",
                        top=5
                    )
                    
                    partial_docs = []
                    async for result in partial_search:
                        partial_docs.append(dict(result))
                    
                    print(f"📦 Partial search returned {len(partial_docs)} documents")
                    for doc in partial_docs:
                        print(f"  document_id: {doc.get('document_id')}")
            
        else:
            print("❌ No documents found in index")
            
    except Exception as e:
        print(f"💥 Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(debug_sec_index())
    except KeyboardInterrupt:
        print("\n🛑 Debug interrupted by user")
    except Exception as e:
        print(f"💥 Debug failed with error: {e}")