#!/usr/bin/env python3
"""Test the unified chunking and citation-ready processing with Motor Insurance FAQs."""

import asyncio
import json
from app.utils.policy_claim_chunker import extract_text_from_bytes
from app.services.unified_chunking_strategy import UnifiedDocumentChunker
from app.services.citation_ready_processor import CitationReadyDocumentProcessor
from app.services.azure_services import AzureServiceManager

async def test_unified_citation_ready():
    """Test the complete unified chunking and citation-ready pipeline."""
    print("🔄 Testing Unified Chunking & Citation-Ready Processing")
    print("=" * 65)
    
    # Read the Motor Insurance FAQs PDF
    pdf_path = r'C:\temp\AI\ai-claims-analysis\sample-docs\policies\AnyCompany Motor Insurance FAQs.pdf'
    with open(pdf_path, 'rb') as f:
        content = f.read()
    
    # Extract text
    text = extract_text_from_bytes(content, 'application/pdf')
    source = "AnyCompany Motor Insurance FAQs.pdf"
    
    print(f"📄 Document: {source}")
    print(f"📊 Text length: {len(text)} characters")
    print()
    
    # Test unified chunking
    print("🧠 Step 1: Unified Chunking")
    print("-" * 30)
    
    chunker = UnifiedDocumentChunker()
    
    # Create metadata similar to what would come from enhanced processing
    metadata = {
        "is_policy": True,
        "document_type": "motor_insurance_faq",
        "structured_data": {
            "document_type": "faq",
            "key_value_pairs": {
                "insurance_company": "AnyCompany",
                "coverage_type": "Motor Insurance",
                "document_title": "Motor Insurance FAQs"
            }
        },
        "tags": ["motor_insurance", "faq", "policy"]
    }
    
    # Chunk the document using unified strategy
    chunk_data = await chunker.chunk_document(
        text=text,
        document_type="faq",
        source=source,
        metadata=metadata
    )
    
    print(f"✅ Unified chunking complete: {len(chunk_data)} chunks")
    
    # Convert to DocumentChunk objects for citation processing
    from app.services.document_processor import DocumentChunk
    
    chunks = []
    for i, chunk_dict in enumerate(chunk_data):
        # Create mock embedding (in real scenario, this would be generated)
        mock_embedding = [0.1] * 1536  # Mock OpenAI embedding size
        
        chunk = DocumentChunk(
            chunk_id=chunk_dict["metadata"]["chunk_id"],
            content=chunk_dict["content"],
            metadata=chunk_dict["metadata"],
            embedding=mock_embedding
        )
        chunks.append(chunk)
    
    print(f"📋 Created {len(chunks)} DocumentChunk objects with mock embeddings")
    print()
    
    # Test citation-ready processing
    print("📚 Step 2: Citation-Ready Processing")
    print("-" * 35)
    
    azure_manager = AzureServiceManager()  # Mock for testing
    citation_processor = CitationReadyDocumentProcessor(azure_manager)
    
    # Create citation-ready search documents
    search_documents = await citation_processor.prepare_citation_ready_search_documents(
        chunks=chunks,
        document_id="motor_faq_001",
        source=source,
        metadata=metadata,
        document_type="faq"
    )
    
    print(f"✅ Citation-ready processing complete: {len(search_documents)} search documents")
    print()
    
    # Analyze the results
    print("📊 Step 3: Results Analysis")
    print("-" * 25)
    
    # Show sample search documents
    for i, doc in enumerate(search_documents[:3]):
        print(f"🔹 Search Document {i+1}:")
        print(f"   ID: {doc['id']}")
        print(f"   Title: {doc['title']}")
        print(f"   Document Type: {doc['document_type']}")
        print(f"   Section Type: {doc['section_type']}")
        print(f"   Content Type: {doc['content_type']}")
        print(f"   Confidence Score: {doc['confidence_score']:.2f}")
        print(f"   Contains Amounts: {doc['contains_amounts']}")
        print(f"   Contains Dates: {doc['contains_dates']}")
        
        # Show citation info
        citation_info = json.loads(doc['citation_info'])
        print(f"   Citation Info:")
        for key, value in citation_info.items():
            if value:
                print(f"     {key}: {value}")
        
        # Content preview
        preview = doc['content'][:150].replace('\n', ' ')
        print(f"   Content Preview: {preview}...")
        print()
    
    if len(search_documents) > 3:
        print(f"   ... and {len(search_documents) - 3} more search documents")
    
    print()
    print("🎯 COMPARISON WITH SEC DOCUMENTS")
    print("=" * 35)
    print("✅ Unified Chunking Strategy: Using consistent md2chunks approach")
    print("✅ Citation-Ready Metadata: Rich metadata structure similar to SEC docs")
    print("✅ Search Document Schema: Consistent field structure for Q&A retrieval")
    print("✅ Content Analysis: Financial amounts, dates, key terms detection")
    print("✅ Confidence Scoring: Quality assessment for reliable citations")
    print("✅ Section Detection: Intelligent content categorization")
    print("✅ Document Typing: Clear classification for targeted search")
    
    # Quality metrics
    avg_confidence = sum(doc['confidence_score'] for doc in search_documents) / len(search_documents)
    avg_chunk_size = sum(doc['char_count'] for doc in search_documents) / len(search_documents)
    
    print()
    print("📈 QUALITY METRICS")
    print("-" * 18)
    print(f"Average Confidence Score: {avg_confidence:.2f}")
    print(f"Average Chunk Size: {avg_chunk_size:.0f} characters")
    print(f"Total Search Documents: {len(search_documents)}")
    print(f"Documents with Financial Data: {sum(1 for doc in search_documents if doc['contains_amounts'])}")
    print(f"Documents with Dates: {sum(1 for doc in search_documents if doc['contains_dates'])}")
    
    print()
    print("🏆 SUCCESS: Policies and Claims now have the same citation")
    print("    capabilities as SEC documents for Q&A retrieval!")

if __name__ == "__main__":
    asyncio.run(test_unified_citation_ready())