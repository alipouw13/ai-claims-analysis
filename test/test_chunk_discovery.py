#!/usr/bin/env python3
"""Test to find chunks using different search methods."""

import asyncio
import logging
from app.services.azure_services import AzureServiceManager
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_chunk_discovery():
    """Test different ways to find chunks."""
    print("🔍 TESTING CHUNK DISCOVERY")
    print("=" * 30)
    
    try:
        # Initialize Azure services
        azure_manager = AzureServiceManager()
        await azure_manager.initialize()
        
        policy_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME
        print(f"📊 Using policy index: {policy_index}")
        
        # Method 1: Search for all documents to see the structure
        print("\n📋 STEP 1: Search for all documents")
        print("-" * 40)
        
        client = azure_manager.get_search_client_for_index(policy_index)
        
        # Get all documents without filters
        results = await client.search(
            search_text="*",
            top=50
        )
        
        all_documents = []
        async for r in results:
            rd = dict(r)
            all_documents.append(rd)
        
        print(f"Found {len(all_documents)} total documents")
        
        if all_documents:
            # Show the structure of the first few documents
            for i, doc in enumerate(all_documents[:3]):
                print(f"\n  Document {i+1}:")
                print(f"    Keys: {list(doc.keys())}")
                print(f"    ID: {doc.get('id')}")
                print(f"    Parent ID: {doc.get('parent_id')}")
                
                # Check for content field variations
                content_field = None
                content_value = None
                for key in ['content', 'chunk', 'text', 'body']:
                    if key in doc and doc[key]:
                        content_field = key
                        content_value = doc[key]
                        break
                
                if content_field:
                    print(f"    Content Field: {content_field}")
                    print(f"    Content Length: {len(content_value)}")
                    preview = content_value[:100].replace('\n', ' ')
                    print(f"    Content Preview: {preview}...")
                else:
                    print(f"    Content: No content found")
                    
                # Check other important fields
                for field in ['title', 'source', 'filename']:
                    if field in doc:
                        print(f"    {field.title()}: {doc[field]}")
            
            # Separate documents with content from metadata-only
            docs_with_content = []
            docs_without_content = []
            
            for doc in all_documents:
                has_content = False
                for content_key in ['content', 'chunk', 'text', 'body']:
                    if content_key in doc and doc[content_key] and len(str(doc[content_key]).strip()) > 10:
                        has_content = True
                        break
                
                if has_content:
                    docs_with_content.append(doc)
                else:
                    docs_without_content.append(doc)
            
            print(f"\n  Documents WITH content: {len(docs_with_content)}")
            print(f"  Documents WITHOUT content (metadata only): {len(docs_without_content)}")
            
            if docs_with_content:
                # Get unique parent IDs from content documents
                content_parent_ids = set()
                for doc in docs_with_content:
                    parent_id = doc.get('parent_id')
                    if parent_id:
                        content_parent_ids.add(parent_id)
                
                print(f"  Unique parent IDs with content: {list(content_parent_ids)[:5]}")
                
                # Test chunk retrieval for first parent ID
                if content_parent_ids:
                    test_parent_id = list(content_parent_ids)[0]
                    print(f"\n📊 STEP 2: Test chunk retrieval for parent_id: {test_parent_id}")
                    print("-" * 60)
                    
                    chunks = await azure_manager.get_chunks_for_document(policy_index, test_parent_id)
                    print(f"Retrieved {len(chunks)} chunks using get_chunks_for_document()")
                    
                    if chunks:
                        print(f"✅ Chunk retrieval working!")
                        for i, chunk in enumerate(chunks[:3]):
                            content_len = len(chunk.get('content', '') or chunk.get('chunk', ''))
                            print(f"   Chunk {i+1}: {content_len} chars")
                    else:
                        print(f"❌ No chunks retrieved")
        
        # Method 2: Search for car insurance content specifically
        print("\n🚗 STEP 3: Search for car insurance content")
        print("-" * 35)
        
        car_results = await client.search(
            search_text="car insurance OR motor insurance OR auto insurance",
            top=10,
            select=["id", "parent_id", "content", "title", "source"]
        )
        
        car_chunks = []
        async for r in car_results:
            rd = dict(r)
            car_chunks.append(rd)
        
        print(f"Found {len(car_chunks)} car insurance chunks")
        
        if car_chunks:
            car_parent_ids = set(chunk.get('parent_id') for chunk in car_chunks if chunk.get('parent_id'))
            print(f"Car insurance parent IDs: {list(car_parent_ids)}")
            
            # Test with car insurance parent ID
            if car_parent_ids:
                car_parent_id = list(car_parent_ids)[0]
                print(f"\n📊 Testing chunk retrieval for car insurance parent_id: {car_parent_id}")
                car_chunks_retrieved = await azure_manager.get_chunks_for_document(policy_index, car_parent_id)
                print(f"Retrieved {len(car_chunks_retrieved)} car insurance chunks")
        
        # Method 3: Search by filename pattern
        print("\n📄 STEP 4: Search by filename patterns")
        print("-" * 30)
        
        filename_results = await client.search(
            search_text="*",
            filter="source ne null",
            top=50,
            select=["id", "parent_id", "source", "title"]
        )
        
        sources = set()
        async for r in filename_results:
            rd = dict(r)
            source = rd.get('source')
            if source:
                sources.add(source)
        
        print(f"Found {len(sources)} unique source files:")
        for source in sorted(sources):
            print(f"  - {source}")
            
        # Look for car insurance file specifically
        car_files = [s for s in sources if 'car' in s.lower() or 'motor' in s.lower() or 'insurance' in s.lower()]
        if car_files:
            print(f"\nCar insurance files found: {car_files}")
        
        print("\n✅ Chunk discovery test complete!")
        print("\nSUMMARY:")
        print(f"- Total documents: {len(all_documents) if 'all_documents' in locals() else 0}")
        print(f"- Documents with content: {len(docs_with_content) if 'docs_with_content' in locals() else 0}")
        print(f"- Documents without content: {len(docs_without_content) if 'docs_without_content' in locals() else 0}")
        print(f"- Unique parent IDs: {len(content_parent_ids) if 'content_parent_ids' in locals() else 0}")
        print(f"- Car insurance chunks: {len(car_chunks) if 'car_chunks' in locals() else 0}")
        print(f"- Source files: {len(sources) if 'sources' in locals() else 0}")
        
    except Exception as e:
        print(f"❌ Error during chunk discovery: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chunk_discovery())