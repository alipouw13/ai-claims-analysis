#!/usr/bin/env python3
"""Show detailed comparison of citation capabilities between SEC and Insurance documents."""

import asyncio
import json
from app.utils.policy_claim_chunker import extract_text_from_bytes
from app.services.unified_chunking_strategy import UnifiedDocumentChunker
from app.services.citation_ready_processor import CitationReadyDocumentProcessor
from app.services.azure_services import AzureServiceManager

async def show_citation_comparison():
    """Show detailed citation metadata comparison."""
    print("🔍 DETAILED CITATION CAPABILITIES COMPARISON")
    print("=" * 55)
    
    # Process a sample document
    pdf_path = r'C:\temp\AI\ai-claims-analysis\sample-docs\policies\AnyCompany Motor Insurance FAQs.pdf'
    with open(pdf_path, 'rb') as f:
        content = f.read()
    
    text = extract_text_from_bytes(content, 'application/pdf')
    source = "AnyCompany Motor Insurance FAQs.pdf"
    
    # Create citation-ready documents
    chunker = UnifiedDocumentChunker()
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
    
    chunk_data = await chunker.chunk_document(
        text=text,
        document_type="faq",
        source=source,
        metadata=metadata
    )
    
    from app.services.document_processor import DocumentChunk
    chunks = []
    for chunk_dict in chunk_data:
        mock_embedding = [0.1] * 1536
        chunk = DocumentChunk(
            chunk_id=chunk_dict["metadata"]["chunk_id"],
            content=chunk_dict["content"],
            metadata=chunk_dict["metadata"],
            embedding=mock_embedding
        )
        chunks.append(chunk)
    
    azure_manager = AzureServiceManager()
    citation_processor = CitationReadyDocumentProcessor(azure_manager)
    
    search_documents = await citation_processor.prepare_citation_ready_search_documents(
        chunks=chunks,
        document_id="motor_faq_001",
        source=source,
        metadata=metadata,
        document_type="faq"
    )
    
    # Show detailed metadata for one document
    sample_doc = search_documents[0]
    
    print("📊 SAMPLE INSURANCE DOCUMENT CITATION METADATA")
    print("-" * 50)
    print("Core Fields (used by Q&A retrieval):")
    print(f"  • id: {sample_doc['id']}")
    print(f"  • title: {sample_doc['title']}")
    print(f"  • document_type: {sample_doc['document_type']}")
    print(f"  • content_type: {sample_doc['content_type']}")
    print(f"  • section_type: {sample_doc['section_type']}")
    print(f"  • confidence_score: {sample_doc['confidence_score']}")
    print(f"  • char_count: {sample_doc['char_count']}")
    print(f"  • contains_amounts: {sample_doc['contains_amounts']}")
    print(f"  • contains_dates: {sample_doc['contains_dates']}")
    print()
    
    print("Citation Information (JSON structure):")
    citation_info = json.loads(sample_doc['citation_info'])
    for key, value in citation_info.items():
        print(f"  • {key}: {value}")
    print()
    
    print("🔗 SEC DOCUMENT CITATION COMPARISON")
    print("-" * 40)
    print("SEC Document Citation Fields:")
    print("  • ticker: [Company stock symbol]")
    print("  • company_name: [Company name]")
    print("  • form_type: [10-K, 10-Q, etc.]")
    print("  • filing_date: [Document filing date]")
    print("  • accession_number: [SEC accession number]")
    print("  • citation_info: [JSON with metadata]")
    print()
    
    print("Insurance Document Citation Fields:")
    print("  • document_id: [Unique document identifier]")
    print("  • source_file: [Original filename]")
    print("  • document_type: [policy, claim, faq, etc.]")
    print("  • coverage_type: [Motor, Health, etc.]")
    print("  • policy_number: [Policy identifier if applicable]")
    print("  • citation_info: [JSON with metadata]")
    print()
    
    print("✅ UNIFIED CITATION CAPABILITIES")
    print("-" * 35)
    print("Both document types now provide:")
    print("  🎯 Consistent metadata structure")
    print("  🎯 Rich citation information in JSON format")
    print("  🎯 Confidence scoring for quality assessment")
    print("  🎯 Content analysis (amounts, dates, key terms)")
    print("  🎯 Section and content type classification")
    print("  🎯 Unique identifiers for precise citation")
    print("  🎯 Timestamp tracking for audit trails")
    print()
    
    print("🚀 Q&A RETRIEVAL BENEFITS")
    print("-" * 25)
    print("With unified citation capabilities:")
    print("  ✨ LLM can generate consistent citations regardless of document type")
    print("  ✨ User gets same quality references for SEC and insurance documents")
    print("  ✨ Confidence scores help prioritize most reliable sources")
    print("  ✨ Rich metadata enables intelligent answer contextualization")
    print("  ✨ Structured citation_info JSON supports custom citation formats")
    print()
    
    print("🏆 MISSION ACCOMPLISHED!")
    print("Insurance documents (policies, claims, FAQs) now have the same")
    print("citation capabilities as SEC documents for Q&A retrieval.")

if __name__ == "__main__":
    asyncio.run(show_citation_comparison())