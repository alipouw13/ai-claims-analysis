import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.document_processor import DocumentProcessor
from app.services.azure_services import AzureServiceManager

async def test_document_id():
    try:
        # Initialize Azure manager
        azure_manager = AzureServiceManager()
        await azure_manager.initialize()
        
        # Create document processor
        processor = DocumentProcessor(azure_manager)
        
        # Test with a provided document ID
        test_document_id = "test-uuid-12345"
        test_content = b"This is a test document content"
        test_metadata = {"is_claim": False}
        
        print(f"Testing with provided document ID: {test_document_id}")
        
        # Call process_document with the document_id parameter
        result = await processor.process_document(
            content=test_content,
            content_type="text/plain",
            source="test.txt",
            metadata=test_metadata,
            document_id=test_document_id
        )
        
        print(f"Result document_id: {result.get('document_id')}")
        print(f"Expected document_id: {test_document_id}")
        print(f"Match: {result.get('document_id') == test_document_id}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_document_id())
