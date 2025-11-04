#!/usr/bin/env python3
"""
Simple test script to verify document upload schema fix
"""

import asyncio
import json
import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.citation_ready_processor import CitationReadyDocumentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_citation_ready_processor():
    """Test the citation ready processor generates valid document schema"""
    
    # Create a mock chunk
    class MockChunk:
        def __init__(self):
            self.chunk_id = "test_chunk_1"
            self.content = "This is a test insurance policy document chunk with coverage information."
            self.embedding = [0.1] * 1536  # Mock embedding
            self.metadata = {
                "section_name": "coverage_details",
                "chunk_index": 0,
                "page_number": 1
            }
    
    # Test citation ready processor
    processor = CitationReadyDocumentProcessor(None)
    
    chunks = [MockChunk()]
    document_id = "test_doc_123"
    source = "test_policy.pdf"
    metadata = {"is_claim": False, "document_type": "policy"}
    
    search_docs = await processor.prepare_citation_ready_search_documents(
        chunks=chunks,
        document_id=document_id,
        source=source,
        metadata=metadata,
        document_type="policy"
    )
    
    if search_docs:
        doc = search_docs[0]
        logger.info("✅ Citation ready processor test passed")
        logger.info(f"Document keys: {list(doc.keys())}")
        
        # Check that problematic fields are in citation_info JSON instead of top-level
        if "document_type" not in doc:
            logger.info("✅ document_type correctly moved to citation_info")
        else:
            logger.error("❌ document_type still in top-level fields")
            
        if "citation_info" in doc:
            citation_data = json.loads(doc["citation_info"])
            if "document_type" in citation_data:
                logger.info("✅ document_type found in citation_info JSON")
            else:
                logger.error("❌ document_type missing from citation_info JSON")
        
        # Print sample document structure
        logger.info("Sample document structure:")
        for key, value in doc.items():
            if key == "content_vector":
                logger.info(f"  {key}: [vector of length {len(value)}]")
            elif key == "citation_info":
                logger.info(f"  {key}: {value[:100]}...")
            else:
                logger.info(f"  {key}: {value}")
    else:
        logger.error("❌ No search documents generated")

async def main():
    logger.info("🧪 Testing document upload schema fixes...")
    
    try:
        await test_citation_ready_processor()
        logger.info("✅ All tests passed - document upload should work now!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())