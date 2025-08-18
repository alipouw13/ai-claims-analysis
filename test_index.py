import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.azure_services import AzureServiceManager
from app.core.config import settings

async def test_index():
    try:
        azure = AzureServiceManager()
        await azure.initialize()
        
        client = azure.get_search_client_for_index(settings.AZURE_SEARCH_POLICY_INDEX_NAME)
        results = await client.search(search_text='*', top=20)
        
        docs = []
        async for r in results:
            docs.append(dict(r))
        
        print(f'Found {len(docs)} documents in policy index')
        print("\nFirst 10 documents:")
        for i, d in enumerate(docs[:10]):
            print(f"{i+1}. ID: {d.get('chunk_id', 'N/A')}")
            print(f"   Parent: {d.get('parent_id', 'N/A')}")
            print(f"   Title: {d.get('title', 'N/A')}")
            print(f"   Source: {d.get('source', 'N/A')}")
            print()
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_index())
