#!/usr/bin/env python3

import asyncio
import sys
import os
import requests

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.azure_services import AzureServiceManager
from app.core.config import settings

async def find_policy_documents():
    """Find the actual document IDs in the policy index"""
    
    print("🔍 Finding actual policy document IDs...")
    
    # Initialize Azure services
    azure_manager = AzureServiceManager()
    await azure_manager.initialize()
    
    # Get policy index name
    policy_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME
    print(f"📊 Searching in index: {policy_index}")
    
    try:
        # List unique documents in policy index
        documents = await azure_manager.list_unique_documents(policy_index)
        print(f"📄 Found {len(documents)} documents in policy index:")
        
        for i, doc in enumerate(documents[:5]):  # Show first 5
            doc_id = doc.get('parent_id') or doc.get('document_id') or doc.get('id')
            title = doc.get('title') or doc.get('source') or 'Unknown'
            print(f"  {i+1}. ID: {doc_id}")
            print(f"      Title: {title}")
            print()
        
        # Test with the first document if available
        if documents:
            test_doc = documents[0]
            test_id = test_doc.get('parent_id') or test_doc.get('document_id') or test_doc.get('id')
            print(f"🎯 Testing enhanced visualization with: {test_id}")
            
            # Test the API endpoint
            base_url = "http://localhost:8000"
            url = f"{base_url}/api/v1/knowledge-base/documents/{test_id}/chunk-visualization?index=policy"
            
            response = requests.get(url)
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                chunk_stats = data.get("chunk_stats", {})
                print(f"✅ SUCCESS! Found {chunk_stats.get('total_chunks', 0)} chunks")
                
                if chunk_stats.get('total_chunks', 0) > 0:
                    print("📊 Enhanced statistics:")
                    print(f"  - Total Content Length: {chunk_stats.get('total_content_length', 0):,}")
                    print(f"  - Avg Chunk Length: {chunk_stats.get('avg_chunk_length', 0):.2f}")
                    print(f"  - Section Types: {len(chunk_stats.get('section_types', []))}")
                    
                    # Show section distribution
                    section_dist = chunk_stats.get('section_distribution', {})
                    if section_dist:
                        print(f"  - Top sections:")
                        for section, count in list(section_dist.items())[:5]:
                            print(f"    * {section}: {count} chunks")
                else:
                    print("❌ No chunks found for this document")
            else:
                print(f"❌ API request failed: {response.text}")
                
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(find_policy_documents())
    except KeyboardInterrupt:
        print("\n🛑 Search interrupted by user")
    except Exception as e:
        print(f"💥 Search failed with error: {e}")