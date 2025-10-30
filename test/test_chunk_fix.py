#!/usr/bin/env python3
"""Test to fix the get_chunks_for_document method."""

import asyncio
import logging
from app.services.azure_services import AzureServiceManager
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fixed_chunk_retrieval():
    """Test the fixed chunk retrieval method."""
    print("🔧 TESTING FIXED CHUNK RETRIEVAL")
    print("=" * 35)
    
    try:
        # Initialize Azure services
        azure_manager = AzureServiceManager()
        await azure_manager.initialize()
        
        policy_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME
        print(f"📊 Using policy index: {policy_index}")
        
        # Get the client
        client = azure_manager.get_search_client_for_index(policy_index)
        
        # Test parent ID (from previous test)
        test_parent_id = "doc_8974dcbf_47630a54b8cd"  # Car insurance policy
        print(f"\n🎯 Testing with parent_id: {test_parent_id}")
        
        # Method 1: Current broken method
        print("\n📊 STEP 1: Test current method")
        print("-" * 30)
        
        current_chunks = await azure_manager.get_chunks_for_document(policy_index, test_parent_id)
        print(f"Current method result: {len(current_chunks)} chunks")
        
        # Method 2: Fixed search - get all fields first
        print("\n📊 STEP 2: Direct search with all fields")
        print("-" * 35)
        
        filter_expr = f"parent_id eq '{test_parent_id}'"
        print(f"Filter: {filter_expr}")
        
        # Search without select to get all fields
        results = await client.search(
            search_text="*",
            filter=filter_expr,
            top=100
        )
        
        direct_chunks = []
        async for r in results:
            rd = dict(r)
            direct_chunks.append(rd)
        
        print(f"Direct search result: {len(direct_chunks)} chunks")
        
        if direct_chunks:
            print("\nFirst chunk analysis:")
            first_chunk = direct_chunks[0]
            print(f"  Keys: {list(first_chunk.keys())[:15]}")
            print(f"  ID: {first_chunk.get('id')}")
            print(f"  Parent ID: {first_chunk.get('parent_id')}")
            print(f"  Title: {first_chunk.get('title', 'no_title')[:50]}")
            
            # Check content fields
            content_fields = ['content', 'chunk', 'text', 'body']
            content_found = None
            for field in content_fields:
                if field in first_chunk and first_chunk[field]:
                    content_found = field
                    content_length = len(first_chunk[field])
                    print(f"  Content field '{field}': {content_length} chars")
                    preview = first_chunk[field][:100].replace('\n', ' ')
                    print(f"  Content preview: {preview}...")
                    break
            
            if not content_found:
                print("  ❌ No content field found!")
        
        # Method 3: Test with corrected select fields
        print("\n📊 STEP 3: Test with corrected select fields")
        print("-" * 40)
        
        # Based on what we found, use the correct fields
        correct_select_fields = ["id", "parent_id", "content", "title", "chunk_id", "section_type"]
        
        try:
            corrected_results = await client.search(
                search_text="*",
                select=correct_select_fields,
                filter=filter_expr,
                top=100
            )
            
            corrected_chunks = []
            async for r in corrected_results:
                rd = dict(r)
                # Normalize for UI compatibility
                normalized = {
                    **rd,
                    "id": rd.get("chunk_id") or rd.get("id"),
                    "content": rd.get("content") or "",
                }
                corrected_chunks.append(normalized)
            
            print(f"Corrected search result: {len(corrected_chunks)} chunks")
            
            if corrected_chunks:
                print("✅ Success! Fixed method working")
                print(f"First chunk content length: {len(corrected_chunks[0].get('content', ''))}")
            
        except Exception as select_error:
            print(f"❌ Select fields error: {select_error}")
            print("Will need to use search without select")
        
        # Method 4: Create a proper fixed method
        print("\n📊 STEP 4: Create proper fixed method")
        print("-" * 35)
        
        async def get_chunks_for_document_fixed(index_name: str, document_id: str, top_k: int = 1000):
            """Fixed version of get_chunks_for_document."""
            try:
                client = azure_manager.get_search_client_for_index(index_name)
                filter_expr = f"parent_id eq '{document_id}'"
                
                # Try with basic select first
                try:
                    results = await client.search(
                        search_text="*",
                        select=["id", "parent_id", "content", "title"],
                        filter=filter_expr,
                        top=top_k,
                    )
                except Exception:
                    # Fallback to no select
                    results = await client.search(
                        search_text="*",
                        filter=filter_expr,
                        top=top_k,
                    )
                
                chunks = []
                async for r in results:
                    rd = dict(r)
                    # Normalize for UI compatibility
                    normalized = {
                        **rd,
                        "id": rd.get("chunk_id") or rd.get("id"),
                        "content": rd.get("content") or "",
                    }
                    chunks.append(normalized)
                
                return chunks
                
            except Exception as e:
                logger.error(f"Failed to get chunks for document '{document_id}': {e}")
                return []
        
        # Test the fixed method
        fixed_chunks = await get_chunks_for_document_fixed(policy_index, test_parent_id)
        print(f"Fixed method result: {len(fixed_chunks)} chunks")
        
        if fixed_chunks:
            print("🎉 SUCCESS! Fixed method works!")
            print(f"Total chunks: {len(fixed_chunks)}")
            print(f"Sample chunk content length: {len(fixed_chunks[0].get('content', ''))}")
            print(f"Sample chunk ID: {fixed_chunks[0].get('id')}")
            
            # Test with chunk visualization format
            print("\n📊 Chunk visualization format test:")
            viz_chunks = []
            total_content_length = 0
            
            for i, c in enumerate(fixed_chunks):
                content = c.get("content") or ""
                total_content_length += len(content)
                viz_chunks.append({
                    "chunk_id": c.get("chunk_id") or c.get("id") or f"chunk_{i}",
                    "content": content,
                    "content_length": len(content),
                    "page_number": c.get("page_number"),
                    "section_type": c.get("section_type", ""),
                    "citation_info": c.get("citation_info", {}),
                })
            
            avg_len = round(total_content_length / len(viz_chunks), 2) if viz_chunks else 0
            print(f"  Formatted chunks: {len(viz_chunks)}")
            print(f"  Average length: {avg_len}")
            print(f"  Total content: {total_content_length} chars")
            print("  ✅ Ready for chunk visualization!")
        
        print("\n✅ Chunk retrieval fix test complete!")
        
    except Exception as e:
        print(f"❌ Error during chunk retrieval test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_chunk_retrieval())