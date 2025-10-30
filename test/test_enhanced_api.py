#!/usr/bin/env python3
"""Test the enhanced chunk visualization API with filename support."""

import asyncio
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_enhanced_api():
    """Test the enhanced chunk visualization API."""
    print("🔧 TESTING ENHANCED CHUNK VISUALIZATION API")
    print("=" * 45)
    
    try:
        # Base URL for the API
        base_url = "http://localhost:8000"
        
        # Test 1: Test with hash-based document ID (should work as before)
        print("\n📊 TEST 1: Hash-based document ID")
        print("-" * 35)
        
        hash_doc_id = "doc_8974dcbf_47630a54b8cd"
        url1 = f"{base_url}/api/v1/knowledge-base/documents/{hash_doc_id}/chunk-visualization?index=policy"
        
        response1 = requests.get(url1)
        
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"✅ Hash ID test successful")
            print(f"   Status: {data1.get('status')}")
            print(f"   Chunks: {len(data1.get('chunks', []))}")
            print(f"   Title: {data1.get('document_info', {}).get('title', 'no_title')}")
        else:
            print(f"❌ Hash ID test failed: {response1.status_code}")
            print(f"   Response: {response1.text[:200]}")
        
        # Test 2: Test with filename (the main fix)
        print("\n📄 TEST 2: Filename-based document ID")
        print("-" * 35)
        
        filename_doc_id = "car_insurance_policy_booklet_11_2023.pdf"
        url2 = f"{base_url}/api/v1/knowledge-base/documents/{filename_doc_id}/chunk-visualization?index=policy"
        
        response2 = requests.get(url2)
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"✅ Filename test successful")
            print(f"   Status: {data2.get('status')}")
            print(f"   Chunks: {len(data2.get('chunks', []))}")
            print(f"   Title: {data2.get('document_info', {}).get('title', 'no_title')}")
            
            if len(data2.get('chunks', [])) > 0:
                print(f"🎉 SUCCESS! Filename lookup now works!")
                print(f"   Frontend should now see chunks for: {filename_doc_id}")
                
                # Show chunk stats
                chunk_stats = data2.get('chunk_stats', {})
                print(f"   Total chunks: {chunk_stats.get('total_chunks', 0)}")
                print(f"   Average length: {chunk_stats.get('avg_chunk_length', 0)}")
                print(f"   Total content: {chunk_stats.get('total_content_length', 0)} chars")
            else:
                print(f"❌ No chunks found even with filename lookup")
        else:
            print(f"❌ Filename test failed: {response2.status_code}")
            print(f"   Response: {response2.text[:200]}")
        
        # Test 3: Test with non-existent document
        print("\n🚫 TEST 3: Non-existent document")
        print("-" * 30)
        
        fake_doc_id = "non_existent_document.pdf"
        url3 = f"{base_url}/api/v1/knowledge-base/documents/{fake_doc_id}/chunk-visualization?index=policy"
        
        response3 = requests.get(url3)
        
        if response3.status_code == 200:
            data3 = response3.json()
            status = data3.get('status')
            print(f"✅ Graceful handling of non-existent document")
            print(f"   Status: {status}")
            if status == "document_not_found":
                print(f"   ✅ Correct status returned")
            else:
                print(f"   ⚠️  Unexpected status: {status}")
        else:
            print(f"❌ Non-existent document test failed: {response3.status_code}")
        
        print(f"\n✅ Enhanced API test complete!")
        print(f"\nSUMMARY:")
        print(f"- Hash ID lookup: {'✅' if response1.status_code == 200 else '❌'}")
        print(f"- Filename lookup: {'✅' if response2.status_code == 200 and len(data2.get('chunks', [])) > 0 else '❌'}")
        print(f"- Error handling: {'✅' if response3.status_code == 200 else '❌'}")
        
        # If filename lookup worked, provide frontend guidance
        if response2.status_code == 200 and len(data2.get('chunks', [])) > 0:
            print(f"\n🎯 FRONTEND IMPACT:")
            print(f"   The chunk visualization should now work in the frontend!")
            print(f"   When users select 'car_insurance_policy_booklet_11_2023.pdf',")
            print(f"   they should see {len(data2.get('chunks', []))} chunks with")
            print(f"   proper document structure visualization.")
        
    except Exception as e:
        print(f"❌ Error during API test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enhanced_api())