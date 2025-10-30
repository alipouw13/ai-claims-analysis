#!/usr/bin/env python3
"""Test the fixed chunk visualization."""

import asyncio
import logging
from app.services.azure_services import AzureServiceManager
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fixed_visualization():
    """Test that chunk visualization now works."""
    print("🎯 TESTING FIXED CHUNK VISUALIZATION")
    print("=" * 40)
    
    try:
        # Initialize Azure services
        azure_manager = AzureServiceManager()
        await azure_manager.initialize()
        
        policy_index = settings.AZURE_SEARCH_POLICY_INDEX_NAME
        print(f"📊 Using policy index: {policy_index}")
        
        # Test with the car insurance policy document ID
        document_id = "doc_8974dcbf_47630a54b8cd"
        print(f"🎯 Testing document ID: {document_id}")
        
        # Test the fixed get_chunks_for_document method
        print("\n📊 Testing fixed get_chunks_for_document method")
        print("-" * 45)
        
        chunks = await azure_manager.get_chunks_for_document(policy_index, document_id, top_k=2000)
        print(f"✅ Retrieved {len(chunks)} chunks")
        
        if chunks:
            # Format for chunk visualization
            viz_chunks = []
            total_content_length = 0
            
            for i, c in enumerate(chunks):
                content = c.get("content") or c.get("chunk") or ""
                total_content_length += len(content)
                viz_chunks.append({
                    "chunk_id": c.get("chunk_id") or c.get("id") or f"chunk_{i}",
                    "content": content,
                    "content_length": len(content),
                    "page_number": c.get("page_number"),
                    "section_type": c.get("section_type", ""),
                    "credibility_score": c.get("credibility_score", 0),
                    "citation_info": c.get("citation_info", {}),
                    "search_score": c.get("@search.score", 0),
                })
            
            avg_len = round(total_content_length / len(viz_chunks), 2) if viz_chunks else 0
            
            # Document info
            document_info = {
                "document_id": document_id,
                "title": chunks[0].get("title") or chunks[0].get("source") or document_id,
                "index": "policy",
                "processed_at": chunks[0].get("processed_at", ""),
                "total_chunks": len(viz_chunks),
            }
            
            # Chunk stats
            chunk_stats = {
                "total_chunks": len(viz_chunks),
                "avg_chunk_length": avg_len,
                "total_content_length": total_content_length,
                "section_types": sorted(list({c.get("section_type", "") for c in chunks if c.get("section_type")})),
            }
            
            # Create the response format for the UI
            response = {
                "document_id": document_id,
                "document_info": document_info,
                "chunks": viz_chunks,
                "chunk_stats": chunk_stats,
                "status": "success"
            }
            
            print(f"📊 Chunk Visualization Results:")
            print(f"  Document: {document_info['title']}")
            print(f"  Total chunks: {chunk_stats['total_chunks']}")
            print(f"  Average chunk length: {chunk_stats['avg_chunk_length']}")
            print(f"  Total content: {chunk_stats['total_content_length']} chars")
            print(f"  Section types: {chunk_stats['section_types'][:5]}")
            
            # Show sample chunks
            print(f"\n📋 Sample chunks:")
            for i, chunk in enumerate(viz_chunks[:3]):
                print(f"  Chunk {i+1}:")
                print(f"    ID: {chunk['chunk_id']}")
                print(f"    Length: {chunk['content_length']} chars")
                print(f"    Section: {chunk['section_type']}")
                preview = chunk['content'][:80].replace('\n', ' ')
                print(f"    Preview: {preview}...")
            
            print(f"\n🎉 SUCCESS! Chunk visualization data ready!")
            print(f"   The frontend should now show {len(viz_chunks)} chunks for this document")
            
        else:
            print("❌ No chunks found - issue not fixed")
        
        # Test with actual filename that might be used in frontend
        print(f"\n📄 Testing with actual filename")
        print("-" * 30)
        
        filename = "car_insurance_policy_booklet_11_2023.pdf"
        filename_chunks = await azure_manager.get_chunks_for_document(policy_index, filename)
        print(f"Chunks for filename '{filename}': {len(filename_chunks)}")
        
        if not filename_chunks:
            print("⚠️  Filename lookup failed - frontend may need document ID mapping")
        
        print("\n✅ Fixed chunk visualization test complete!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_visualization())