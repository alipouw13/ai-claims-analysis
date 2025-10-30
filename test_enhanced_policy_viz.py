#!/usr/bin/env python3

import asyncio
import requests
import json

async def test_enhanced_policy_visualization():
    """Test the enhanced policy chunk visualization"""
    
    print("🎯 Testing Enhanced Policy Chunk Visualization")
    print("=" * 60)
    
    # Test with a known policy document (from the screenshot)
    base_url = "http://localhost:8000"
    
    # Use the car insurance policy document that was shown in the screenshot
    document_id = "car_insurance_policy_booklet_TL_2023.pdf"
    
    print(f"📄 Testing with document: {document_id}")
    
    try:
        # Test the enhanced chunk visualization
        url = f"{base_url}/api/v1/knowledge-base/documents/{document_id}/chunk-visualization?index=policy"
        
        print(f"🔍 Making request to: {url}")
        response = requests.get(url)
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n✅ SUCCESS! Enhanced visualization data:")
            print("-" * 40)
            
            # Document info
            doc_info = data.get("document_info", {})
            print(f"📋 Document Info:")
            print(f"  - Title: {doc_info.get('title', 'N/A')}")
            print(f"  - Document Type: {doc_info.get('document_type', 'N/A')}")
            print(f"  - Company: {doc_info.get('company', 'N/A')}")
            print(f"  - Source: {doc_info.get('source', 'N/A')}")
            print(f"  - File Size: {doc_info.get('file_size', 'N/A')}")
            print(f"  - Processed At: {doc_info.get('processed_at', 'N/A')}")
            
            # Chunk statistics
            chunk_stats = data.get("chunk_stats", {})
            print(f"\n📊 Enhanced Chunk Statistics:")
            print(f"  - Total Chunks: {chunk_stats.get('total_chunks', 0)}")
            print(f"  - Avg Chunk Length: {chunk_stats.get('avg_chunk_length', 0):.2f}")
            print(f"  - Total Content Length: {chunk_stats.get('total_content_length', 0):,}")
            print(f"  - Min Chunk Length: {chunk_stats.get('min_chunk_length', 0)}")
            print(f"  - Max Chunk Length: {chunk_stats.get('max_chunk_length', 0)}")
            
            page_range = chunk_stats.get('page_range', {})
            print(f"  - Page Range: {page_range.get('min', 'N/A')} - {page_range.get('max', 'N/A')}")
            
            print(f"  - Avg Credibility Score: {chunk_stats.get('avg_credibility_score', 0):.3f}")
            print(f"  - Total Sections: {chunk_stats.get('total_sections', 0)}")
            
            # Section distribution
            section_dist = chunk_stats.get('section_distribution', {})
            if section_dist:
                print(f"\n🏷️  Section Distribution:")
                for section, count in list(section_dist.items())[:10]:  # Show top 10
                    print(f"    - {section}: {count} chunks")
            
            # Section types
            section_types = chunk_stats.get('section_types', [])
            if section_types:
                print(f"\n📑 Section Types ({len(section_types)} total):")
                print(f"    {', '.join(section_types[:10])}")  # Show first 10
                if len(section_types) > 10:
                    print(f"    ... and {len(section_types) - 10} more")
            
            # Sample chunks
            chunks = data.get("chunks", [])
            if chunks:
                print(f"\n📦 Sample Chunks (showing first 3 of {len(chunks)}):")
                for i, chunk in enumerate(chunks[:3]):
                    print(f"  Chunk {i+1}:")
                    print(f"    - ID: {chunk.get('chunk_id', 'N/A')}")
                    print(f"    - Length: {chunk.get('content_length', 0)} chars")
                    print(f"    - Section: {chunk.get('section_type', 'N/A')}")
                    print(f"    - Page: {chunk.get('page_number', 'N/A')}")
                    print(f"    - Credibility: {chunk.get('credibility_score', 0):.3f}")
                    content_preview = chunk.get('content', '')[:100] + "..." if len(chunk.get('content', '')) > 100 else chunk.get('content', '')
                    print(f"    - Preview: {content_preview}")
                    print()
            
            print("🎉 Enhanced policy chunk visualization is working!")
            print("\nThis should now provide rich analytics similar to SEC documents.")
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error: {error_data}")
            except:
                print(f"Response text: {response.text}")
    
    except Exception as e:
        print(f"💥 Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_enhanced_policy_visualization())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"💥 Test failed with error: {e}")