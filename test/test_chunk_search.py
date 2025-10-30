#!/usr/bin/env python3
"""Test to verify chunk search and document ID matching."""

import asyncio
import logging
from app.services.azure_services import AzureServiceManager
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_chunk_search():
    """Test chunk search functionality to debug visualization issue."""
    print("🔍 TESTING CHUNK SEARCH FUNCTIONALITY")
    print("=" * 45)
    
    try:
        # Initialize Azure services
        azure_manager = AzureServiceManager()
        await azure_manager.initialize()
        print("✅ Azure services initialized")
        
        # Get the policy index name
        policy_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME
        print(f"📊 Using policy index: {policy_index}")
        
        # List all documents in the policy index to see what's there
        print("\n📋 STEP 1: List all documents in policy index")
        print("-" * 40)
        
        all_docs = await azure_manager.list_unique_documents(policy_index, top_k=500)
        print(f"Found {len(all_docs)} documents in index")
        
        # Show first few documents
        for i, doc in enumerate(all_docs[:5]):
            doc_id = doc.get('document_id') or doc.get('parent_id') or doc.get('id', 'no_id')
            title = doc.get('title', 'no_title')[:50]
            content_length = len(doc.get('content', '') or doc.get('chunk', ''))
            print(f"  {i+1}. ID: {doc_id}")
            print(f"      Title: {title}")
            print(f"      Content Length: {content_length}")
            print(f"      Keys: {list(doc.keys())[:10]}")
            print()
            
        if len(all_docs) > 5:
            print(f"  ... and {len(all_docs) - 5} more documents")
        
        # Look for car insurance policy specifically
        print("\n🚗 STEP 2: Search for car insurance policy")
        print("-" * 35)
        
        car_docs = []
        for doc in all_docs:
            title = doc.get('title', '').lower()
            content = doc.get('content', '') or doc.get('chunk', '')
            
            if 'car' in title or 'motor' in title or 'insurance' in content.lower()[:200]:
                car_docs.append(doc)
        
        print(f"Found {len(car_docs)} car insurance related documents")
        
        if car_docs:
            # Get unique document IDs for car insurance
            unique_doc_ids = set()
            for doc in car_docs:
                doc_id = doc.get('document_id') or doc.get('parent_id')
                if doc_id:
                    unique_doc_ids.add(doc_id)
            
            print(f"Unique car insurance document IDs: {list(unique_doc_ids)}")
            
            # Test chunk retrieval for each document ID
            print("\n🧩 STEP 3: Test chunk retrieval")
            print("-" * 30)
            
            for doc_id in unique_doc_ids:
                print(f"\nTesting document ID: {doc_id}")
                chunks = await azure_manager.get_chunks_for_document(policy_index, doc_id)
                print(f"  Found {len(chunks)} chunks")
                
                if chunks:
                    # Show first chunk details
                    first_chunk = chunks[0]
                    print(f"  First chunk ID: {first_chunk.get('id', 'no_id')}")
                    print(f"  First chunk content length: {len(first_chunk.get('content', '') or first_chunk.get('chunk', ''))}")
                    print(f"  First chunk parent_id: {first_chunk.get('parent_id', 'no_parent_id')}")
                    print(f"  First chunk keys: {list(first_chunk.keys())[:10]}")
                    
                    # Check for content
                    content = first_chunk.get('content', '') or first_chunk.get('chunk', '')
                    if content:
                        print(f"  Content preview: {content[:100]}...")
                    else:
                        print("  ⚠️  No content found in chunk!")
                        
                else:
                    print("  ❌ No chunks found for this document ID")
        else:
            print("❌ No car insurance documents found")
            
        # Test with a specific known document ID from the frontend
        print("\n🎯 STEP 4: Test with car_insurance_policy_booklet_11_2023.pdf")
        print("-" * 55)
        
        known_filename = "car_insurance_policy_booklet_11_2023.pdf"
        test_chunks = await azure_manager.get_chunks_for_document(policy_index, known_filename)
        print(f"Chunks found for '{known_filename}': {len(test_chunks)}")
        
        if not test_chunks:
            # Try searching for any document containing this filename
            print("Searching for documents containing this filename...")
            for doc in all_docs:
                if known_filename in str(doc.get('title', '')) or known_filename in str(doc.get('source', '')):
                    print(f"Found matching document: {doc.get('id')} / {doc.get('document_id')} / {doc.get('parent_id')}")
                    print(f"  Title: {doc.get('title')}")
                    print(f"  Source: {doc.get('source')}")
        
        print("\n🎯 STEP 5: List recent documents (last 10)")
        print("-" * 40)
        
        # Sort by processed_at if available
        sorted_docs = sorted(all_docs, 
                           key=lambda x: x.get('processed_at', ''), 
                           reverse=True)
        
        for i, doc in enumerate(sorted_docs[:10]):
            doc_id = doc.get('document_id') or doc.get('parent_id') or doc.get('id')
            title = doc.get('title', 'no_title')[:40]
            processed = doc.get('processed_at', 'no_date')[:19]
            print(f"  {i+1}. {doc_id} | {title} | {processed}")
        
        print("\n✅ Chunk search test complete!")
        
    except Exception as e:
        print(f"❌ Error during chunk search test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chunk_search())